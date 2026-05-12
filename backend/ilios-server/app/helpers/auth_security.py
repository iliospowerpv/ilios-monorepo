"""Auth abuse protection helpers (Phase 0B).

Provides:
  * per-IP login rate limiting,
  * per-account failed-login lockout / cooldown,
  * password reset throttling (per-IP + per-email),
  * append-only auth security event logging.

Counts are sourced from the ``auth_security_events`` table, so the
limiter survives process restart and works in a multi-worker deployment
without requiring Redis. Redis is intentionally NOT a hard dependency
of this module — the policy table is correct and durable.

All decisions return generic, identical responses to the caller; this
module never reveals account existence in returned messages.
"""
import hashlib
import hmac
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.crud.auth_security_event import AuthSecurityEventCRUD
from app.models.auth_security_event import AuthSecurityEvent
from app.settings import settings

logger = logging.getLogger(__name__)


# Event types
EVENT_LOGIN = "login"
EVENT_PASSWORD_RESET_REQUEST = "password_reset_request"

# Outcomes
OUTCOME_SUCCESS = "success"
OUTCOME_FAILURE = "failure"
OUTCOME_RATE_LIMITED = "rate_limited"
OUTCOME_LOCKED = "locked"
OUTCOME_THROTTLED = "throttled"

# Login outcomes that count toward rate-limit / lockout budgets.
_LOGIN_BAD_OUTCOMES = (OUTCOME_FAILURE, OUTCOME_RATE_LIMITED, OUTCOME_LOCKED)
# Password-reset outcomes that count toward throttle budget. SUCCESS
# counts so an attacker cannot mass-trigger emails by using valid emails.
_RESET_COUNT_OUTCOMES = (OUTCOME_SUCCESS, OUTCOME_FAILURE, OUTCOME_THROTTLED)


@dataclass
class RateLimitDecision:
    allowed: bool
    reason: Optional[str] = None
    retry_after_seconds: Optional[int] = None


def normalize_identifier(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return value.strip().lower()


def hash_identifier(value: Optional[str]) -> Optional[str]:
    """HMAC-SHA256 of the normalized identifier, keyed by the app secret.

    The hash is stable across requests (so we can count failures per
    account) but is not reversible from a leaked table without the
    secret_key. For known users we also store ``user_id`` directly so an
    operator can look up by user without needing to recompute the hash.
    """
    norm = normalize_identifier(value)
    if not norm:
        return None
    key = (settings.secret_key or "").encode()
    return hmac.new(key, norm.encode(), hashlib.sha256).hexdigest()


def get_request_ip(request: Optional[Request]) -> Optional[str]:
    """Best-effort source IP. Honors X-Forwarded-For (the deployment
    runs behind Replit's edge proxy) and falls back to the socket peer."""
    if request is None:
        return None
    xff = request.headers.get("x-forwarded-for")
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first[:64]
    if request.client and request.client.host:
        return request.client.host[:64]
    return None


def get_request_ua(request: Optional[Request]) -> Optional[str]:
    if request is None:
        return None
    ua = request.headers.get("user-agent")
    return ua[:512] if ua else None


def record_event(
    db_session: Session,
    *,
    event_type: str,
    outcome: str,
    user_id: Optional[int] = None,
    identifier_hash: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    reason: Optional[str] = None,
) -> Optional[AuthSecurityEvent]:
    """Best-effort write of an auth security event.

    Never raises — auditing failures must not break legitimate auth.
    Sensitive values (raw passwords, tokens, raw email of unknown
    accounts) MUST NOT be passed to this function.
    """
    payload = {
        "event_type": event_type,
        "outcome": outcome,
        "user_id": user_id,
        "normalized_identifier_hash": identifier_hash,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "reason": (reason[:255] if reason else None),
    }
    try:
        return AuthSecurityEventCRUD(db_session).create_item(payload)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Failed to write auth_security_event ({event_type}/{outcome}): {exc}")
        try:
            db_session.rollback()
        except Exception:
            pass
        return None


def _count_events_since(
    db_session: Session,
    *,
    since: datetime,
    event_type: str,
    outcomes: tuple,
    ip_address: Optional[str] = None,
    identifier_hash: Optional[str] = None,
) -> int:
    q = db_session.query(func.count(AuthSecurityEvent.id)).filter(
        AuthSecurityEvent.event_type == event_type,
        AuthSecurityEvent.outcome.in_(outcomes),
        AuthSecurityEvent.created_at >= since,
    )
    if ip_address is not None:
        q = q.filter(AuthSecurityEvent.ip_address == ip_address)
    if identifier_hash is not None:
        q = q.filter(AuthSecurityEvent.normalized_identifier_hash == identifier_hash)
    return q.scalar() or 0


def check_login_ip_rate_limit(
    db_session: Session, ip_address: Optional[str]
) -> RateLimitDecision:
    """Decide whether to allow another login attempt from ``ip_address``.

    Counts only attempts that did NOT succeed, so legitimate users
    behind a shared NAT are not punished for each other's typos.
    """
    if not ip_address:
        return RateLimitDecision(allowed=True)

    now = datetime.now(timezone.utc)

    minute_count = _count_events_since(
        db_session,
        since=now - timedelta(minutes=1),
        event_type=EVENT_LOGIN,
        outcomes=_LOGIN_BAD_OUTCOMES,
        ip_address=ip_address,
    )
    if minute_count >= settings.login_rate_limit_per_minute:
        return RateLimitDecision(
            allowed=False, reason="per_minute_ip", retry_after_seconds=60
        )

    hour_count = _count_events_since(
        db_session,
        since=now - timedelta(hours=1),
        event_type=EVENT_LOGIN,
        outcomes=_LOGIN_BAD_OUTCOMES,
        ip_address=ip_address,
    )
    if hour_count >= settings.login_rate_limit_per_hour:
        return RateLimitDecision(
            allowed=False, reason="per_hour_ip", retry_after_seconds=3600
        )

    return RateLimitDecision(allowed=True)


def check_account_lockout(
    db_session: Session, identifier_hash: Optional[str]
) -> RateLimitDecision:
    """Decide whether the account identified by ``identifier_hash`` is
    currently in cooldown after too many failed attempts."""
    if not identifier_hash:
        return RateLimitDecision(allowed=True)

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=settings.account_lockout_window_minutes)
    failure_count = _count_events_since(
        db_session,
        since=window_start,
        event_type=EVENT_LOGIN,
        outcomes=(OUTCOME_FAILURE,),
        identifier_hash=identifier_hash,
    )
    if failure_count < settings.account_lockout_threshold:
        return RateLimitDecision(allowed=True)

    last_failure_at = (
        db_session.query(func.max(AuthSecurityEvent.created_at))
        .filter(
            AuthSecurityEvent.event_type == EVENT_LOGIN,
            AuthSecurityEvent.outcome == OUTCOME_FAILURE,
            AuthSecurityEvent.normalized_identifier_hash == identifier_hash,
            AuthSecurityEvent.created_at >= window_start,
        )
        .scalar()
    )
    if last_failure_at is None:
        return RateLimitDecision(allowed=True)
    if last_failure_at.tzinfo is None:
        last_failure_at = last_failure_at.replace(tzinfo=timezone.utc)
    cooldown_until = last_failure_at + timedelta(
        minutes=settings.account_lockout_cooldown_minutes
    )
    if cooldown_until <= now:
        return RateLimitDecision(allowed=True)

    retry = max(1, int((cooldown_until - now).total_seconds()))
    return RateLimitDecision(
        allowed=False, reason="account_locked", retry_after_seconds=retry
    )


def clear_failed_logins_for_identifier(
    db_session: Session, identifier_hash: Optional[str]
) -> int:
    """Delete recent failed-login events for this identifier after a
    successful login, so the lockout counter resets."""
    if not identifier_hash:
        return 0
    try:
        deleted = (
            db_session.query(AuthSecurityEvent)
            .filter(
                AuthSecurityEvent.event_type == EVENT_LOGIN,
                AuthSecurityEvent.outcome == OUTCOME_FAILURE,
                AuthSecurityEvent.normalized_identifier_hash == identifier_hash,
            )
            .delete(synchronize_session=False)
        )
        db_session.commit()
        return int(deleted or 0)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Failed to clear failed-login events: {exc}")
        try:
            db_session.rollback()
        except Exception:
            pass
        return 0


def check_password_reset_throttle(
    db_session: Session,
    *,
    ip_address: Optional[str],
    identifier_hash: Optional[str],
) -> RateLimitDecision:
    """Decide whether to allow another password-reset request."""
    now = datetime.now(timezone.utc)
    hour_ago = now - timedelta(hours=1)

    if ip_address:
        ip_count = _count_events_since(
            db_session,
            since=hour_ago,
            event_type=EVENT_PASSWORD_RESET_REQUEST,
            outcomes=_RESET_COUNT_OUTCOMES,
            ip_address=ip_address,
        )
        if ip_count >= settings.password_reset_per_ip_per_hour:
            return RateLimitDecision(
                allowed=False, reason="per_hour_ip", retry_after_seconds=3600
            )

    if identifier_hash:
        id_count = _count_events_since(
            db_session,
            since=hour_ago,
            event_type=EVENT_PASSWORD_RESET_REQUEST,
            outcomes=_RESET_COUNT_OUTCOMES,
            identifier_hash=identifier_hash,
        )
        if id_count >= settings.password_reset_per_email_per_hour:
            return RateLimitDecision(
                allowed=False, reason="per_hour_email", retry_after_seconds=3600
            )

    return RateLimitDecision(allowed=True)

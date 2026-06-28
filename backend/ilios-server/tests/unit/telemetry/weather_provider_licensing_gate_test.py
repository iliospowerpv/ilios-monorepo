"""Weather provider licensing-acknowledgement gate (Phase D hardening) — DB-free.

These tests lock in the DEFAULT-DENY licensing gate enforced by the provider
import router helpers:

* ``_licensing_requires_ack`` exempts ONLY an explicit unrestricted allowlist;
  every other class (``free_noncommercial``, ``commercial``, and any
  unknown/future string) is restricted and needs an acknowledged account first.
* ``_resolve_provider_pull_context`` refuses a restricted-licence pull that has no
  account, or an account whose licensing was never acknowledged — INCLUDING the
  keyless free-tier case (Open-Meteo, ``free_noncommercial``) that previously
  slipped through because only ``commercial`` was gated.
* An acknowledged keyless account (``secret_name`` NULL) resolves cleanly and
  never touches the durable credential store.
* An explicitly unrestricted provider still pulls account-lessly (no regression).

They monkeypatch the catalog/account CRUDs with in-memory fakes (mirroring the
service tests) so no DB or live HTTP is required.
"""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models.weather import WeatherProviderAccountStatus
from app.routers import weather as wx
from app.schema.weather import ProviderImportRequest


def _catalog(*, licensing="free_noncommercial", enabled=True, config_schema=None):
    return SimpleNamespace(
        provider_key="open_meteo",
        is_enabled=enabled,
        licensing_class=licensing,
        capabilities_json={},
        config_schema=config_schema if config_schema is not None else {},
    )


def _account(*, acknowledged_at=None, secret_name=None, status=None):
    return SimpleNamespace(
        id=7,
        provider_key="open_meteo",
        company_id=1,
        is_archived=False,
        status=status or WeatherProviderAccountStatus.active,
        licensing_acknowledged_at=acknowledged_at,
        secret_name=secret_name,
    )


def _patch_cruds(monkeypatch, *, catalog, account=None):
    monkeypatch.setattr(
        wx, "WeatherProviderCatalogCRUD",
        lambda db: SimpleNamespace(get_by_key=lambda key: catalog),
    )
    monkeypatch.setattr(
        wx, "WeatherProviderAccountCRUD",
        lambda db: SimpleNamespace(
            get_for_company=lambda *, company_id, account_id: account
        ),
    )


def _req(account_id=None):
    return ProviderImportRequest(
        provider_key="open_meteo",
        account_id=account_id,
        window_start=datetime(2024, 6, 1, 0, 0),
        window_end=datetime(2024, 6, 1, 3, 0),
        metrics=None,
        granularity="hourly",
    )


class _ExplodingStore:
    """A credential store that fails if anyone ever reads a secret."""

    def retrieve(self, secret_name):  # pragma: no cover - must never be called
        raise AssertionError(
            f"durable credential store must not be read for keyless pull: {secret_name!r}"
        )


def _resolve(monkeypatch, *, catalog, account=None, account_id=None, read=False):
    _patch_cruds(monkeypatch, catalog=catalog, account=account)
    return wx._resolve_provider_pull_context(
        None,
        site=SimpleNamespace(company_id=1),
        request_body=_req(account_id=account_id),
        credential_store=_ExplodingStore(),
        read_credentials=read,
    )


# ---------------------------------------------------------------------------
# The helper — default-deny
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "licensing",
    ["", "public_domain", "open_data", "unrestricted", "OPEN", " Open ", None],
)
def test_unrestricted_or_undeclared_classes_need_no_ack(licensing):
    # An explicit unrestricted class — or an undeclared one (None/"" -> "") — is
    # exempt; the gate only fires on a positively-declared restrictive class.
    assert wx._licensing_requires_ack(licensing) is False


@pytest.mark.parametrize(
    "licensing",
    ["free_noncommercial", "noncommercial", "commercial", "some_future_tier"],
)
def test_restricted_and_unknown_nonempty_classes_need_ack(licensing):
    # Default-deny for any positively-declared class that is not on the allowlist,
    # including unrecognised/future strings.
    assert wx._licensing_requires_ack(licensing) is True


# ---------------------------------------------------------------------------
# The gate — keyless free_noncommercial (the hole that was closed)
# ---------------------------------------------------------------------------
def test_keyless_restricted_without_account_is_blocked(monkeypatch):
    with pytest.raises(HTTPException) as ei:
        _resolve(monkeypatch, catalog=_catalog(), account_id=None)
    assert ei.value.status_code == 422
    assert "restricted use" in ei.value.detail


def test_keyless_restricted_unacknowledged_account_is_blocked(monkeypatch):
    with pytest.raises(HTTPException) as ei:
        _resolve(
            monkeypatch,
            catalog=_catalog(),
            account=_account(acknowledged_at=None),
            account_id=7,
        )
    assert ei.value.status_code == 422
    assert "acknowledged on the account" in ei.value.detail


def test_keyless_restricted_acknowledged_account_resolves_without_credential_read(
    monkeypatch,
):
    catalog = _catalog()
    account = _account(acknowledged_at=datetime(2026, 6, 1, 0, 0), secret_name=None)
    resolved_catalog, resolved_account, credentials = _resolve(
        monkeypatch, catalog=catalog, account=account, account_id=7, read=True
    )
    assert resolved_catalog is catalog
    assert resolved_account is account
    # Keyless: no secret_name -> durable store is never touched, credentials empty.
    assert credentials == {}


# ---------------------------------------------------------------------------
# No regressions
# ---------------------------------------------------------------------------
def test_unrestricted_provider_still_pulls_without_account(monkeypatch):
    catalog = _catalog(licensing="public_domain")
    resolved_catalog, account, credentials = _resolve(
        monkeypatch, catalog=catalog, account_id=None
    )
    assert resolved_catalog is catalog
    assert account is None
    assert credentials == {}


def test_commercial_without_account_still_blocked(monkeypatch):
    with pytest.raises(HTTPException) as ei:
        _resolve(monkeypatch, catalog=_catalog(licensing="commercial"), account_id=None)
    assert ei.value.status_code == 422


def test_disabled_provider_is_blocked_before_licensing(monkeypatch):
    with pytest.raises(HTTPException) as ei:
        _resolve(monkeypatch, catalog=_catalog(enabled=False), account_id=None)
    assert ei.value.status_code == 400
    assert "disabled" in ei.value.detail

from sqlalchemy import Column, DateTime, ForeignKey, Identity, Index, Integer, String, desc
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class AuthSecurityEvent(Base):
    """Append-only record of authentication-related security events:
    successful login, failed login, rate-limited login, account lockout
    triggered, password reset requested, password reset throttled.

    Sensitive values (passwords, tokens, raw email of unknown accounts)
    are never stored. For unknown identifiers the
    ``normalized_identifier_hash`` column carries an HMAC of the
    normalized email so multiple attempts against the same identifier
    can be counted without disclosing the raw value.
    """

    __tablename__ = "auth_security_events"

    __table_args__ = (
        Index("ix_auth_security_events_created_at", desc("created_at")),
        Index(
            "ix_auth_security_events_identifier_created",
            "normalized_identifier_hash",
            desc("created_at"),
        ),
        Index("ix_auth_security_events_ip_created", "ip_address", desc("created_at")),
        Index("ix_auth_security_events_event_outcome", "event_type", "outcome"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    created_at = Column(DateTime, server_default=utcnow(), nullable=False)
    event_type = Column(String(64), nullable=False)
    outcome = Column(String(32), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    normalized_identifier_hash = Column(String(128), nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    reason = Column(String(255), nullable=True)

    user = relationship("User")

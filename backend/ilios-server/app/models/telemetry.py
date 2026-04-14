import enum

from sqlalchemy import CheckConstraint, Column, DateTime, Enum, ForeignKey, Identity, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class DASProvidersEnum(enum.Enum):
    kmc = "KMC"
    also_energy = "Also Energy"


class CompanyDASProvider(Base):
    __tablename__ = "company_das_providers"
    __table_args__ = (
        UniqueConstraint("company_id", "provider", name="uq_company_das_provider"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    provider = Column(Enum(DASProvidersEnum), nullable=False)

    created_at = Column(DateTime, server_default=utcnow())

    company = relationship("Company", back_populates="das_providers")


class DASConnectionOwnerType(enum.Enum):
    company = "company"
    portfolio = "portfolio"


class DASConnection(Base):
    __tablename__ = "das_connections"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    provider = Column(Enum(DASProvidersEnum), nullable=False)
    secret_token_name = Column(String, nullable=False)
    
    owner_type = Column(String(20), nullable=False, default="company")
    owner_company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    
    last_test_at = Column(DateTime, nullable=True)
    last_test_status = Column(String(20), nullable=True)
    last_test_message = Column(String(500), nullable=True)

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    company = relationship("Company", back_populates="das_connections", foreign_keys=[company_id])
    owner_company = relationship("Company", foreign_keys=[owner_company_id])
    site_mapping = relationship("TelemetrySiteMapping", back_populates="connection", uselist=False)


class TelemetrySiteMapping(Base):
    __tablename__ = "telemetry_sites_mapping"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    # set unique constraint to limit the number of checks per each site
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), unique=True)
    connection_id = Column(Integer, ForeignKey("das_connections.id", ondelete="SET NULL"))

    telemetry_site_id = Column(String, nullable=False)
    telemetry_site_name = Column(String, nullable=False)

    site = relationship("Site", back_populates="telemetry_mapping")
    connection = relationship("DASConnection", back_populates="site_mapping")

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())


class TelemetryDeviceMapping(Base):
    __tablename__ = "telemetry_devices_mapping"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    # set unique constraint to limit the number of checks per each device
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), unique=True, nullable=False)

    telemetry_device_id = Column(String, nullable=False)
    telemetry_device_name = Column(String, nullable=False)

    device = relationship("Device", back_populates="telemetry_mapping")

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())

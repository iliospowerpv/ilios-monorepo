import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Identity, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class DASProvidersEnum(enum.Enum):
    # Make sure enum name is same as in telemetry
    kmc = "KMC"
    also_energy = "Also Energy"


class DASConnection(Base):
    __tablename__ = "das_connections"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    provider = Column(Enum(DASProvidersEnum), nullable=False)
    secret_token_name = Column(String, nullable=False)

    # setting up the server_default value, that will be filled on the database side
    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    company = relationship("Company", back_populates="das_connections")
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

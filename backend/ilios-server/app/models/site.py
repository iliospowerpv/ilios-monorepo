import enum

from sqlalchemy import (
    ARRAY,
    JSON,
    NUMERIC,
    VARCHAR,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Identity,
    Integer,
    String,
    desc,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression

from app.db.base_class import Base
from app.models.board import BoardRelatedEntityTypeExtraEnum, RelatedBoards
from app.models.device import DeviceStatuses
from app.models.file import FileParsingStatuses
from app.models.helpers import utcnow
from app.static import DASConnectionStatus


class State(enum.Enum):
    AK = "AK"
    AL = "AL"
    AR = "AR"
    AZ = "AZ"
    CA = "CA"
    CO = "CO"
    CT = "CT"
    DC = "DC"
    DE = "DE"
    FL = "FL"
    GA = "GA"
    HI = "HI"
    IA = "IA"
    ID = "ID"
    IL = "IL"
    IN = "IN"
    KS = "KS"
    KY = "KY"
    LA = "LA"
    MA = "MA"
    MD = "MD"
    ME = "ME"
    MI = "MI"
    MN = "MN"
    MO = "MO"
    MS = "MS"
    MT = "MT"
    NC = "NC"
    ND = "ND"
    NE = "NE"
    NH = "NH"
    NJ = "NJ"
    NM = "NM"
    NV = "NV"
    NY = "NY"
    OH = "OH"
    OK = "OK"
    OR = "OR"
    PA = "PA"
    RI = "RI"
    SC = "SC"
    SD = "SD"
    TN = "TN"
    TX = "TX"
    UT = "UT"
    VA = "VA"
    VT = "VT"
    WA = "WA"
    WI = "WI"
    WV = "WV"
    WY = "WY"


class SiteWeather(Base):
    __tablename__ = "sites_weather"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"))

    weather_description = Column(VARCHAR, nullable=True)
    weather_icon_url = Column(VARCHAR, nullable=True)

    site = relationship("Site", back_populates="weather", uselist=False)

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())


class Site(RelatedBoards, Base):
    __tablename__ = "sites"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))

    name = Column(VARCHAR, nullable=False)
    address = Column(VARCHAR, nullable=False)
    city = Column(VARCHAR, nullable=False)
    state = Column(Enum(State), nullable=False)
    county = Column(VARCHAR, nullable=True)
    zip_code = Column(VARCHAR, nullable=False)
    system_size_ac = Column(Float, nullable=False)
    system_size_dc = Column(Float, nullable=False)
    lon_lat_url = Column(VARCHAR, nullable=False)

    cameras_uuids = Column(ARRAY(String))

    company = relationship("Company", back_populates="sites")
    devices = relationship("Device", back_populates="site")
    documents = relationship("Document", back_populates="site")
    co_terminus_check = relationship("CoTerminusCheck", back_populates="site", uselist=False)
    telemetry_mapping = relationship("TelemetrySiteMapping", back_populates="site", uselist=False)
    # temporary table to store the user-input fields for the Asset Management view,
    # might be substituted with DD values once all agreements added
    additional_fields = relationship("SiteAdditionalFieldList", back_populates="site", uselist=False)
    # order by updated_at to have the latest available weather for a site
    weather = relationship("SiteWeather", back_populates="site", order_by=desc(SiteWeather.updated_at))

    # setting up the server_default value, that will be filled on the database side
    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())

    _allowed_users = relationship("User", secondary="user_projects", back_populates="sites", overlaps="_allowed_users")

    def get_active_users_ids(self, permissions_module_name):
        """Filter full list of allowed users to return only users who complete registration"""
        return [
            user.id
            for user in self._allowed_users
            if user.is_registered and user.role and user.role.permissions.get(permissions_module_name, {}).get("view")
        ]

    def get_affected_devices_ids(self):
        """Filter full list of allowed devices to return only devices that are not decommissioned"""
        return [device.id for device in self.devices if device.status != DeviceStatuses.decommissioned]

    def get_alerts_ids(self):
        """Filter full list of allowed alert ids related to site devices"""
        site_alert_ids = []
        for device in self.devices:
            site_alert_ids.extend([alert.id for alert in device.alerts if not alert.is_resolved])
        return site_alert_ids

    @property
    def documents_board(self):
        """Site default document board"""
        documents_boards = [
            related_entity.board
            for related_entity in self.related_boards
            if related_entity.extra_entity_type == BoardRelatedEntityTypeExtraEnum.document
        ]
        if documents_boards:
            return documents_boards[0]

    @property
    def das_connection(self):
        return (
            self.telemetry_mapping.connection
            if (self.telemetry_mapping and self.telemetry_mapping.connection_id)
            else None
        )

    @property
    def telemetry_site_name(self):
        return self.telemetry_mapping.telemetry_site_name if self.telemetry_mapping else None

    @property
    def das_connection_name(self):
        return self.telemetry_mapping.connection.name if self.das_connection else None

    @property
    def das_connection_status(self):
        return DASConnectionStatus.connected if self.das_connection else DASConnectionStatus.not_connected

    def get_document(self, document_name):
        documents = [doc for doc in self.documents if doc.name == document_name]
        return documents[0] if documents else None

    @property
    def latest_weather_info(self):
        return self.weather[0] if self.weather else None


class CoTerminusCheck(Base):
    __tablename__ = "co_terminus_checks"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    # set unique constraint to limit the number of checks per each site
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), unique=True)

    status = Column(Enum(FileParsingStatuses), nullable=True)
    result = Column(JSON, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)

    # represents if the check values are the most recent
    is_actual = Column(Boolean, nullable=False, default=True, server_default=expression.true())

    site = relationship("Site", back_populates="co_terminus_check", uselist=False)

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())


class SiteStatuses(enum.Enum):
    construction = "Construction"
    placed_in_service = "Placed in Service"
    decommissioned = "Decommissioned"
    sold = "Sold"


class LeasePaymentFrequencies(enum.Enum):
    monthly = "Monthly"
    quarterly = "Quarterly"
    semi_annual = "Semi Annual"
    annual = "Annual"


class LeasePaymentMethods(enum.Enum):
    check = "Check"
    credit_card = "Credit Card"
    wire = "Wire"


class OfftakerTypes(enum.Enum):
    community_solar = "Community Solar"
    individual = "Individual"
    utility_provider = "Utility Provider"


class MountTypes(enum.Enum):
    canopy = "Canopy"
    carport = "Carport"
    dual_axis = "Dual Axis"
    fixed_tilt = "Fixed Tilt"
    single_axis = "Single Axis"


class SiteAdditionalFieldList(RelatedBoards, Base):
    __tablename__ = "site_additional_fields"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"))

    # "site level details" card
    status = Column(Enum(SiteStatuses), nullable=True)
    project_id = Column(VARCHAR, nullable=True)
    pvsyst = Column(VARCHAR, nullable=True)
    greenhouse_gas_offset = Column(VARCHAR, nullable=True)
    incentive_program = Column(VARCHAR, nullable=True)
    das_provider = Column(VARCHAR, nullable=True)
    das_account = Column(VARCHAR, nullable=True)
    das_username = Column(VARCHAR, nullable=True)
    das_password = Column(VARCHAR, nullable=True)

    # "EPC Contractor" card
    epc_address = Column(VARCHAR, nullable=True)
    epc_contact_name = Column(VARCHAR, nullable=True)
    epc_contact_email = Column(VARCHAR, nullable=True)
    epc_contact_phone = Column(VARCHAR, nullable=True)

    # "Vegetation Vendor" card - shortened to 'vv'
    vv_provider = Column(VARCHAR, nullable=True)
    vv_address = Column(VARCHAR, nullable=True)
    vv_contact_name = Column(VARCHAR, nullable=True)
    vv_contact_email = Column(VARCHAR, nullable=True)
    vv_contact_phone = Column(VARCHAR, nullable=True)

    # "Site Lease" card
    payment_due_date = Column(Date, nullable=True)
    lease_payment_method = Column(Enum(LeasePaymentMethods), nullable=True)
    lease_payment_frequency = Column(Enum(LeasePaymentFrequencies), nullable=True)
    landlord_contact_phone = Column(VARCHAR, nullable=True)

    # "Asset Overview" card
    battery_storage = Column(VARCHAR, nullable=True)
    mount_type = Column(Enum(MountTypes), nullable=True)
    dc_wiring_loss = Column(NUMERIC, nullable=True)
    ac_wiring_loss = Column(NUMERIC, nullable=True)
    medium_voltage_loss = Column(NUMERIC, nullable=True)
    mv_line_loss = Column(NUMERIC, nullable=True)

    # "Tax Equity" card
    tax_equity_fund = Column(VARCHAR, nullable=True)
    tax_equity_provider = Column(VARCHAR, nullable=True)
    tax_equity_buyout_amount = Column(NUMERIC, nullable=True)
    tax_equity_buyout_date = Column(Date, nullable=True)
    tax_equity_pref_rate = Column(NUMERIC, nullable=True)
    smartsheet_data_tape = Column(VARCHAR, nullable=True)

    # "O&M" card
    om_address = Column(VARCHAR, nullable=True)
    om_contact_name = Column(VARCHAR, nullable=True)
    om_contact_email = Column(VARCHAR, nullable=True)
    om_contact_phone = Column(VARCHAR, nullable=True)
    o_and_m_rate = Column(NUMERIC, nullable=True)

    # "Community Solar Manager" card - shortened to 'csm'
    csm_provider = Column(VARCHAR, nullable=True)
    csm_address = Column(VARCHAR, nullable=True)
    csm_contact_name = Column(VARCHAR, nullable=True)
    csm_contact_email = Column(VARCHAR, nullable=True)
    csm_contact_phone = Column(VARCHAR, nullable=True)
    csm_fee = Column(NUMERIC, nullable=True)
    escalator = Column(NUMERIC, nullable=True)
    escalator_effective = Column(Date, nullable=True)

    # "Compliance" card
    entity = Column(VARCHAR, nullable=True)
    bank = Column(VARCHAR, nullable=True)
    report_due_date = Column(Date, nullable=True)
    fiscal_year_end = Column(Date, nullable=True)
    tax_return_deadline = Column(Date, nullable=True)

    # "Ownership" card
    ownership_structure = Column(VARCHAR, nullable=True)
    hold_co = Column(VARCHAR, nullable=True)
    project_co = Column(VARCHAR, nullable=True)
    tax_credit_fund = Column(VARCHAR, nullable=True)

    # "Key dates" card
    permission_to_operate = Column(Date, nullable=True)
    placed_in_service_date = Column(Date, nullable=True)
    financial_close_date = Column(Date, nullable=True)

    # "Interconnection Utility Provider" card - shortened to 'iut'
    iut_address = Column(VARCHAR, nullable=True)
    iut_contact_name = Column(VARCHAR, nullable=True)
    iut_contact_email = Column(VARCHAR, nullable=True)
    iut_contact_phone = Column(VARCHAR, nullable=True)
    utility_rate = Column(VARCHAR, nullable=True)

    # "Insurance provider" card
    insurance_provider = Column(VARCHAR, nullable=True)
    insurance_address = Column(VARCHAR, nullable=True)

    # "Offtaker" card
    offtaker_name = Column(VARCHAR, nullable=True)
    offtaker_type = Column(Enum(OfftakerTypes), nullable=True)
    credit_rating = Column(VARCHAR, nullable=True)
    rating_agency = Column(VARCHAR, nullable=True)
    date_of_rating = Column(Date, nullable=True)

    site = relationship("Site", back_populates="additional_fields", uselist=False)

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())

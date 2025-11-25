import enum

from sqlalchemy import VARCHAR, Column, Date, DateTime, Enum, ForeignKey, Identity, Integer
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow
from app.static import DASConnectionStatus


class DeviceStatuses(enum.Enum):
    available_inventory = "Available Inventory"
    decommissioned = "Decommissioned"
    placed_in_service = "Placed in Service"
    rma = "RMA"
    deleted_on_das = "Deleted on DAS"


class DeviceCategories(enum.Enum):
    inverter = "Inverter"
    rack_mount = "Rack Mount"
    battery = "Battery"
    camera = "Camera"
    combiner_box = "Combiner Box"
    mbod_gateway = "MBOD Gateway"
    meter = "Meter"
    modem = "Modem"
    module = "Module"
    network_connection = "Network Connection"
    network_gateway = "Network Gateway"
    transformer = "Transformer"
    weather_station = "Weather Station"


class DeviceTypes(enum.Enum):
    """
    All possible device types.
    By adding/removing the type also update types in app/helpers/device_helper divided by category or add new type
    category.
    Related schema types: category_types_mapper.
    """

    # inverter
    string = "String"
    micro_inverter = "Micro Inverter"
    power_optimizers = "Power Optimizers"
    # rack mount
    canopy = "Canopy"
    carport = "Carport"
    dual_axis = "Dual Axis"
    fixed_tilt = "Fixed Tilt"
    single_axis = "Single Axis"
    # battery
    agm = "AGM"
    flow = "Flow"
    lithium_ion = "Lithium Ion"
    nickel_cadmium = "Nickel Cadmium"
    # camera
    bullet = "Bullet"
    cctv = "CCTV"
    dome = "Dome"
    ptz = "PTZ"
    thermal = "Thermal"
    # module
    bifacial = "Bifacial"
    monofacial = "Monofacial"
    # network connection
    cellular_internet = "Internet via Cellular"
    fiber_internet = "Internet via Fiber"
    satellite_internet = "Internet via Satellite"
    terrestrial_internet = "Internet via Terrestrial"
    point_to_point = "Point to Point"
    vpn = "VPN"
    # transformer
    ground = "Ground"
    inverter_transformer = "Inverter Transformer"
    collector = "Collector"
    auxiliary = "Auxiliary"
    earthing = "Earthing"
    voltage_regulator = "Voltage Regulator"
    # weather station, not used after https://softserve-jirasw.atlassian.net/browse/IOSP1-1158, but let's keep it
    temperature = "Temperature"
    irradiance = "Irradiance"
    rain = "Rain"
    wind = "Wind"
    barometric_pressure = "Barometric Pressure"
    humidity = "Humidity"
    # other
    other = "Other"


class DeviceManufacturers(enum.Enum):
    """
    All possible device manufacturers.
    By adding/removing the manufacturer also update manufacturers in app/helpers/device_helper divided by category
    or add new manufacturer category.
    Related schema types: category_manufacturers_mapper.
    """

    # inverter
    chint_power_systems = "Chint Power Systems"
    sma = "SMA"
    sungrow = "Sungrow"
    advanced_energy = "Advanced Energy"
    alencon_systems = "Alencon Systems"
    chilicon_power = "Chilicon Power"
    cybo_energy = "Cybo Energy"
    enphase_energy = "Enphase Energy"
    fimer = "FIMER"
    fronius_international = "Fronius International"
    ginlong_technologies_co = "Ginlong Technologies Co"
    goodwe = "Goodwe"
    growatt = "Growatt"
    huawei = "Huawei"
    kaco_new_energy_gmbh = "KACO New Energy GmbH"
    midnite_solar = "MidNite Solar"
    nep = "NEP"
    outback_power = "OutBack Power"
    power_electronics = "Power Electronics"
    schneider_electric = "Schneider Electric"
    solaredge = "SolarEdge"
    tmeic = "TMEIC"
    # battery
    nine_sun_solar = "9Sun Solar"
    abb_ltd = "ABB Ltd"
    absen_energy = "Absen Energy"
    bloom_energy = "Bloom Energy"
    byd = "BYD"
    electriq_power = "Electriq Power"
    ess_tech_in = "ESS Tech In"
    fluence = "Fluence"
    lg_chem = "LG Chem"
    neovolta = "NeoVolta"
    nexera_energy = "NexEra Energy"
    panasonic = "Panasonic"
    saft_batteries = "Saft Batteries"
    samsung_sdi = "Samsung SDI"
    siemens = "Siemens"
    sonnen = "Sonnen"
    tesla = "Tesla"
    toshiba = "Toshiba"
    # module
    aditi_solar = "Aditi Solar"
    ae_solar = "AE Solar"
    ascent_solar = "Ascent Solar"
    auxin_solar_inc = "Auxin Solar Inc."
    axitech = "Axitech"
    bluesun = "Bluesun"
    canadian_solar = "Canadian Solar"
    certainteed_solar = "CertainTeed Solar"
    c_sun = "C Sun"
    first_solar = "First Solar"
    hanwha_q_cells = "Hanwha Q Cells"
    hareon = "Hareon"
    heliene = "Heliene"
    ht_saae = "HT-SAAE"
    ja_solar_holdings = "JA Solar Holdings"
    jinkosolar = "JinkoSolar"
    kyocera = "Kyocera"
    lg_electronics = "LG Electronics"
    longi_solar = "LONGi Solar"
    mission_solar = "Mission Solar"
    rec = "REC"
    slifab_solar = "Slifab Solar"
    solar4america = "Solar4America"
    sunpower = "SunPower"
    suntech_power = "Suntech Power"
    trina_solar = "Trina Solar"
    yingli_solar = "Yingli Solar"
    # network connection
    at_n_t = "AT&T"
    cricket = "Cricket"
    charter_communications = "Charter Communications (Spectrum)"
    spacex = "SpaceX"
    sprint = "Sprint"
    t_mobile = "T-Mobile"
    verizon = "Verizon"
    xfinity = "Xfinity"
    other = "Other"
    # rack mount
    crossrail = "Crossrail"
    panel_claw = "Panel Claw"
    terrasmart = "Terrasmart"
    voyager = "Voyager"
    fiveb_solar = "5B Solar"
    allearth_renewables = "AllEarth Renewables"
    apa_solar_racking = "APA Solar Racking"
    array_technologies = "Array Technologies"
    bci_engineering = "BCI Engineering"
    clenergy = "Clenergy"
    ecofasten = "EcoFasten"
    empery_solar = "Empery Solar"
    ftc_solar = "FTC Solar"
    ironridge = "IronRidge"
    kb_racking_inc = "KB Racking Inc."
    magerack = "Magerack"
    m_bar = "M Bar"
    nuance_energy = "Nuance Energy"
    omco_solar = "OMCO Solar"
    prosolar = "ProSolar"
    quick_mount_pv = "Quick Mount PV"
    rbi = "RBI"
    renusol = "Renusol"
    roof_tech = "Roof Tech"
    snapnrack = "SnapNrack"
    sky_grip = "Sky Grip"
    solarpod = "SolarPod"
    sollega_inc = "Sollega Inc"
    sun_action = "Sun Action"
    sun_modo_corp = "Sun Modo Corp"
    suntelite = "Suntelite"
    unirac = "Unirac"


class DeviceWarrantyPeriodOptions(enum.Enum):
    active = "Active"
    end_of_life = "End of Life"


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"))

    # General Info section
    status = Column(Enum(DeviceStatuses))
    asset_id = Column(VARCHAR)
    name = Column(VARCHAR)
    category = Column(Enum(DeviceCategories))
    type = Column(Enum(DeviceTypes), nullable=True)
    manufacturer = Column(Enum(DeviceManufacturers), nullable=True)
    model = Column(VARCHAR)
    serial_number = Column(VARCHAR)
    warranty_effective_date = Column(Date, nullable=True)
    warranty_term = Column(VARCHAR, nullable=True)
    gateway_id = Column(VARCHAR, nullable=True)
    function_id = Column(VARCHAR, nullable=True)
    driver = Column(VARCHAR, nullable=True)
    install_date = Column(Date, nullable=True)
    decommissioned_date = Column(Date, nullable=True)
    # might be substituted with 'updated_at', but this business requirements is not discussed with the customer yet,
    # so we need to have it as a separate user-manageable fields
    last_updated_date = Column(Date, nullable=True)

    # service detail section
    lifetime = Column(VARCHAR, nullable=True)
    warranty_period = Column(Enum(DeviceWarrantyPeriodOptions), nullable=True)
    next_scheduled_service_date = Column(Date, nullable=True)

    # technical details, structure depends on the device category, use json field for storage
    technical_details = Column(JSON, nullable=True)

    site = relationship("Site", back_populates="devices")
    alerts = relationship("Alert", back_populates="device")
    documents = relationship("DeviceDocument", back_populates="device")
    tasks = relationship("Task", back_populates="affected_device")
    telemetry_mapping = relationship("TelemetryDeviceMapping", back_populates="device", uselist=False)

    # setting up the server_default value, that will be filled on the database side
    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    @property
    def das_connection_status(self):
        """Return connection status based on:
        - device Telemetry mapping
        - site Telemetry mapping
        since it depends if connection exists on site level"""
        return self.site.das_connection_status if self.telemetry_mapping else DASConnectionStatus.not_connected

    @property
    def das_connection_active(self):
        """Boolean implementation of <das_connection_status> property, to indicate if device mapping is valid"""
        return self.das_connection_status == DASConnectionStatus.connected


class DeviceOrderByFieldEnum(str, enum.Enum):

    id = "id"
    asset_id = "asset_id"
    name = "name"
    type = "type"
    category = "category"

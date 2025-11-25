import axios, { AxiosInstance } from 'axios';
import type { Params } from './user';
import { Dayjs } from 'dayjs';

interface Items {
  id: string;
  name: string;
  sites_number: number;
  total_capacity: number;
}
interface Companies {
  skip: number;
  limit: number;
  total: number;
  items: Items[];
}

interface Site {
  company_id: number;
  name: string;
  stage: string;
  status: string;
  state: string;
  ownership_structure: string;
  system_size: number;
  tax_equity_amount: number;
  project_value: number;
  mc_month: number;
  mc_year: number;
  itc: number;
  id: number;
}
interface Sites {
  skip: number;
  limit: number;
  total: number;
  items: Site[];
}

interface CreateSiteAttributes {
  company_id?: number;
  name: string;
  address: string;
  city: string;
  state: string;
  county?: string;
  zip_code: string;
  system_size_ac: number;
  system_size_dc: number;
  lon_lat_url: string;
  cameras_uuids?: string[];
}

interface CreateSiteResponse {
  id: number;
  message: string;
  code: number;
}

interface Contractor {
  name: string;
  email: string;
  phone: number;
  address: string;
  company_type: string;
  id: number;
}

interface Contractors {
  skip: number;
  limit: number;
  total: number;
  items: Contractor[];
}

interface CompanyDetails {
  name: string;
  email: string | null;
  phone: string | null;
  address: string | null;
  company_type: string;
  id: number;
  total_sites: number;
  sites_placed_in_service: number;
  sites_under_construction: number;
  total_capacity: number;
  sites_decommissioned: number;
  sites_sold: number;
}

interface CreateDeviceResponse {
  message: string;
  code: number;
  device_id: number;
}

interface CreateDeviceAttributes {
  name: string;
  category: string;
  telemetry_device_id?: string | null;
  telemetry_device_name?: string | null;
}

interface Device {
  asset_id: string;
  status: string;
  name: string;
  category: string;
  type: string;
  manufacturer: string;
  model: string;
  serial_number: string;
  id: number;
  health: string;
  capacity: number;
  warranty_effective_date: string;
  warranty_term: string;
  link_to_warranty_document: string;
  issue: string;
  maintenance: string;
  next_scheduled_service_date: string;
  install_date: string;
  decommissioned_date: string;
  uptime_availability: string;
  lifetime: string;
}
interface Devices {
  skip: number;
  limit: number;
  total: number;
  items: Device[];
}

interface SiteDetailedInfo {
  name: string;
  address: string;
  city: string;
  state: string;
  county: string;
  zip_code: string;
  system_size_ac: number;
  system_size_dc: number;
  das:
    | 'Also Energy'
    | 'Chint Monitoring System'
    | 'LocusNOC'
    | 'Mana Monitoring System'
    | 'Solarlog'
    | 'Solarenview'
    | 'Sunny Portal';
  lon_lat_url: string;
  cameras_uuids: string[];
  id: number;
  company: {
    name: string;
    email: string | null;
    phone: string | null;
    address: string | null;
    company_type:
      | 'O&M Contractor'
      | 'Project/Site Owner'
      | 'EPC Contractor'
      | 'Bank'
      | 'Appraiser'
      | 'Engineering Firm'
      | 'Law Firm'
      | 'Investor'
      | 'Subscriber Manager'
      | 'Insurance Company';
    id: number;
  };
  account: string;
  username: string;
  password: string;
  das_connection_name: string;
  telemetry_site_name: string;
}

interface SiteDetails {
  name: string;
  address: string;
  city: string;
  state: string;
  county?: string | null;
  zip_code: string;
  system_size_ac: number;
  system_size_dc: number;
  lon_lat_url: string;
  cameras_uuids?: Array<any> | null;
  status?: string | null;
  project_id?: string | null;
  pvsyst?: string | null;
  greenhouse_gas_offset?: string | null;
  incentive_program?: string | null;
  das_provider?: string | null;
  das_account?: string | null;
  das_username?: string | null;
  das_password?: string | null;
  year_one_expected_production: string | null;
  degradation_amount: string | null;
  capacity_as_percent_of_total_portfolio?: number;
}

interface SiteAssetOverview {
  battery_storage?: string | null;
  module_quantity: string | null;
  inverter_quantity: string | null;
  project_type: string | null;
  mount_type?: string | null;
  dc_wiring_loss: number | null;
  ac_wiring_loss: number | null;
  medium_voltage_loss: number | null;
  mv_line_loss: number | null;
}

interface SiteOwnership {
  ownership_structure?: string | null;
  hold_co?: string | null;
  project_co?: string | null;
  guarantor: string | null;
  tax_credit_fund?: string | null;
}

interface SiteTaxEquity {
  tax_equity_fund?: string | null;
  tax_equity_provider?: string | null;
  tax_equity_buyout_amount?: number | null;
  tax_equity_buyout_date?: string | null;
  tax_equity_pref_rate?: number | null;
  smartsheet_data_tape?: string | null;
}

interface SiteKeyDates {
  permission_to_operate?: string | null;
  placed_in_service_date?: string | null;
  financial_close_date?: string | null;
  mechanical_completion_date: string | null;
  substantial_completion_date: string | null;
  final_completion_date: string | null;
}

interface SiteOAndM {
  om_address?: string | null;
  om_contact_name?: string | null;
  om_contact_email?: string | null;
  om_contact_phone?: string | null;
  provider: string | null;
  agreement_effective_date: string | null;
  o_and_m_rate?: number | null;
  o_and_m_escalator: string | null;
  production_guarantee: string | null;
}

interface SiteInterconnection {
  iut_address?: string | null;
  iut_contact_name?: string | null;
  iut_contact_email?: string | null;
  iut_contact_phone?: string | null;
  utility_rate?: string | null;
  provider: string | null;
  ppa_term: string | null;
  ppa_effective_date: string | null;
  production_guarantee: string | null;
  interconnection_agreement_effective_date: string | null;
  remaining_ppa_term: string | null;
}

interface SiteEpcContractor {
  epc_address?: string | null;
  epc_contact_name?: string | null;
  epc_contact_email?: string | null;
  epc_contact_phone?: string | null;
  provider: string | null;
  agreement_effective_date: string | null;
}

interface CommunitySolarManager {
  csm_provider?: string | null;
  csm_address?: string | null;
  csm_contact_name?: string | null;
  csm_contact_email?: string | null;
  csm_contact_phone?: string | null;
  csm_fee?: number | null;
  escalator?: number | null;
  escalator_effective?: string | null;
}
interface SiteInsuranceProvider {
  insurance_provider?: string | null;
  insurance_address?: string | null;
}

interface SiteVegetationVendor {
  vv_provider?: string | null;
  vv_address?: string | null;
  vv_contact_name?: string | null;
  vv_contact_phone?: string | null;
  vv_contact_email?: string | null;
}

interface SiteOfftaker {
  offtaker_name?: string | null;
  offtaker_type?: string | null;
  credit_rating?: string | null;
  rating_agency?: string | null;
  date_of_rating?: string | null;
}

interface SiteCompliance {
  entity?: string | null;
  bank?: string | null;
  report_due_date?: string | null;
  fiscal_year_end?: string | null;
  tax_return_deadline?: string | null;
}

interface SiteLease {
  rent_escalator?: string | null;
  payment_due_date?: string | null;
  lease_payment_method?: string | null;
  lease_payment_frequency?: string | null;
  landlord_contact_phone?: string | null;
  landlord: string | null;
  tenant: string | null;
  property_size: string | null;
  effective_date: string | null;
  rent_commencement: string | null;
  rent_amount: string | null;
  rent_escalator_effective_date: string | null;
  initial_term: string | null;
  renewal_terms: string | null;
}

interface DetailedSiteInfo {
  site_level_details: SiteDetails;
  asset_overview: SiteAssetOverview;
  ownership: SiteOwnership;
  tax_equity: SiteTaxEquity;
  key_dates: SiteKeyDates;
  o_and_m: SiteOAndM;
  interconnection: SiteInterconnection;
  epc_contractor: SiteEpcContractor;
  community_solar_manager: CommunitySolarManager;
  insurance_provider: SiteInsuranceProvider;
  vegetation_vendor: SiteVegetationVendor;
  offtaker: SiteOfftaker;
  compliance: SiteCompliance;
  site_lease: SiteLease;
}

interface InverterDeviceTechnicalDetails {
  array: {
    derate: number | string;
    integrated_combiners: string;
    modules_per_string: number | string;
    number_of_strings: number | string;
    yearly_degradation: number | string;
  };
  communication: {
    ip_address: string;
    port: number | null;
    serial_mode: string;
    baud: number | null;
  };
  module: {
    watts_per_module: number | string;
    mpp_voltage: number | string;
    mpp_current: number | string;
    mpp_watts: number | string;
    temperature_coefficient: number | string;
  };
  power: {
    ac_max_output: number | string;
    ac_power: number | string;
    dc_max_input: number | string;
    dc_power: number | string;
    rated_output: number | string;
    standby_power: number | string;
    cec_efficiency: number | string;
    pv_modules_number: number | string;
  };
}

interface MeterDeviceTechnicalDetails {
  general: {
    capacity: null | number;
    inverters: null | number;
  };
  communication: {
    ip_address: null | string;
    unit_id: null | number;
  };
  scale_factor: {
    power: null | number;
    energy: null | number;
    swap_delivered_received: null | string;
    gross_energy: null | string;
  };
  sample_date: {
    kw: null | number;
    kwh_net: null | number;
    kwh_received: null | number;
    kwh_delivered: null | number;
  };
  data_range: {
    max_power: null | number;
    max_voltage: null | number;
    max_current_per_phase: null | number;
    ac: null | string;
  };
}

interface InverterFormFields {
  derate: string;
  integrated_combiners: string;
  modules_per_string: string;
  number_of_strings: number;
  yearly_degradation: string;
  ip_address: string;
  port: string;
  serial_mode: string;
  baud: string;
  watts_per_module: string;
  mpp_voltage: string;
  mpp_current: string;
  mpp_watts: string;
  temperature_coefficient: string;
  ac_max_output: string;
  ac_power: string;
  dc_max_input: string;
  dc_power: string;
  rated_output: string;
  standby_power: string;
  cec_efficiency: number;
  pv_modules_number: number;
}

interface ModuleDeviceTechnicalDetails {
  module_specs: {
    cable_and_connector: number | string;
    frame: number | string;
    glass_type: number | string;
    module_kw: number | string;
    solar_cell_type: number | string;
    solar_cells_per_module: number | string;
    weight: number | string;
  };
  power: {
    mpp_current: number | string;
    mpp_voltage: number | string;
    mpp_watts: number | string;
    power_output: number | string;
    system_voltage: number | string;
    temperature_coefficient: number | string;
    watts_per_module: number | string;
    year_1_degradation: number;
    annual_degradation: number;
    max_power_tolerance: number;
    min_power_tolerance: number;
    power_thermal_coefficient: number;
  };
}

interface ModuleFormFields {
  cable_and_connector: string;
  frame: string;
  glass_type: string;
  module_kw: string;
  solar_cell_type: string;
  solar_cells_per_module: string;
  weight: string;
  mpp_current: string;
  mpp_voltage: string;
  mpp_watts: string;
  power_output: string;
  system_voltage: string;
  temperature_coefficient: string;
  watts_per_module: string;
  year_1_degradation: number;
  annual_degradation: number;
  max_power_tolerance: number;
  min_power_tolerance: number;
  power_thermal_coefficient: number;
}

interface ModemDeviceTechnicalDetails {
  communication: {
    ip_address: string;
    port: number | null;
    serial_mode: string;
    baud: number | null;
  };
}

interface ModemFormFields {
  ip_address: string;
  port: string;
  serial_mode: string;
  baud: string;
}

interface RackMountDeviceTechnicalDetails {
  general: {
    azimuth: number | string;
    racking_capacity: number | string;
    tracking: string;
  };
}

interface RackMountFormFields {
  azimuth: string;
  racking_capacity: string;
  tracking: string;
}

interface TransformerDeviceTechnicalDetails {
  frequency: null | string;
  phase: null | string;
  rating: null | string;
  type: null | string;
  voltage: null | number;
  volts: null | number;
}

interface NetworkConnectionDeviceTechnicalDetails {
  account_number: null | string;
  provider: null | string;
}

interface CameraDeviceTechnicalDetails {
  communication: {
    ip_address: string;
  };
}

interface CameraFormFields {
  ip_address: string;
}

interface BatteryDeviceTechnicalDetails {
  report: null | string;
  report_due_date: null | string;
  size_kw: null | number;
  size_mwh: null | number;
}
interface WeatherStationTechnicalDetails {
  communication: {
    ip_address: null | string;
    port: null | number;
    serial_mode: null | string;
    baud: null | number;
  };
  sensors: {
    wind: null | string;
    humidity: null | string;
    barometer: null | string;
    snow_depth: null | string;
    normal_incidence_pyrheliometer: null | string;
    rain: null | string;
    temperature: null | string;
    irradiance: null | string;
  };
  temperature_sensors: {
    ambient_temperature: null | string;
    panel_temperature1: null | string;
    panel_temperature2: null | string;
    min_temperature: null | number;
    max_temperature: null | number;
  };
  pyranometer_sensors: {
    reference: null | string;
    azimuth_and_tilt: null | string;
    azimuth: null | number;
    tilt: null | number;
    tracking: null | string;
    pyranometer: null | string;
  };
  monthly_insolation: {
    january: null | number;
    february: null | number;
    march: null | number;
    april: null | number;
    may: null | number;
    june: null | number;
    july: null | number;
    august: null | number;
    september: null | number;
    october: null | number;
    november: null | number;
    december: null | number;
    insolation_reference: null | string;
    interpolate_daily_insolation: null | string;
  };
}

interface CombinerBoxDeviceTechnicalDetails {
  dimensions: null | string;
  enclosure_type: null | string;
  input_circuits_max_count: null | number;
  max_output: null | number;
  weight: null | number;
}

interface TechnicalDetailAttributes {
  category:
    | 'Inverter'
    | 'Rack Mount'
    | 'Battery'
    | 'Camera'
    | 'Combiner Box'
    | 'MBOD Gateway'
    | 'Meter'
    | 'Modem'
    | 'Module'
    | 'Network Connection'
    | 'Network Gateway'
    | 'Transformer'
    | 'Weather Station';
  technical_details:
    | InverterDeviceTechnicalDetails
    | ModuleDeviceTechnicalDetails
    | ModemDeviceTechnicalDetails
    | RackMountDeviceTechnicalDetails
    | CameraDeviceTechnicalDetails
    | MeterDeviceTechnicalDetails
    | TransformerDeviceTechnicalDetails
    | NetworkConnectionDeviceTechnicalDetails
    | BatteryDeviceTechnicalDetails
    | CombinerBoxDeviceTechnicalDetails
    | WeatherStationTechnicalDetails;
}

type Category = 'Warranty' | 'Specifications';

interface Document {
  id: number;
  author: string;
  filename: string;
  extension: string;
  created_at: string;
}

interface Documents {
  category: Category;
  items: Document[];
}

interface ServiceDetailCardFormFields {
  availability?: string | undefined;
  failure_rate?: string | undefined;
  warranty_period?: 'Active' | 'End of Life' | undefined;
  lifetime?: string | undefined;
  mtbr?: string | undefined;
  mttr?: string | undefined;
  next_scheduled_service_date?: Dayjs | null | undefined;
  open_repair_tickets_count?: number | undefined;
  test_interval?: string | undefined;
}

interface ServiceDetailAttributes {
  lifetime?: string | null;
  warranty_period?: string | null;
  next_scheduled_service_date?: string | null;
}

interface UpdateDeviceGeneralInfoAttributes {
  asset_id: string;
  status: 'Available Inventory' | 'Decommissioned' | 'Placed in Service' | 'RMA';
  name: string;
  type: string | null;
  manufacturer: string | null;
  model: string;
  serial_number: string;
  warranty_effective_date: string | null;
  warranty_term: string | null;
  gateway_id: string | null;
  function_id: string | null;
  driver: string | null;
  install_date: string | null;
  decommissioned_date: string | null;
  last_updated_date: string | null;
  telemetry_device_id?: string | null;
  telemetry_device_name?: string | null;
}

interface UpdateDeviceGeneralInfoParams {
  siteId: number;
  deviceId: number;
  attributes: UpdateDeviceGeneralInfoAttributes;
}

interface DeviceGeneralInfo {
  asset_id: string;
  status: 'Available Inventory' | 'Decommissioned' | 'Placed in Service' | 'RMA';
  name: string;
  category:
    | 'Inverter'
    | 'Rack Mount'
    | 'Battery'
    | 'Camera'
    | 'Combiner Box'
    | 'MBOD Gateway'
    | 'Meter'
    | 'Modem'
    | 'Module'
    | 'Network Connection'
    | 'Network Gateway'
    | 'Transformer'
    | 'Weather Station';
  type: string | null;
  manufacturer: string | null;
  model: string;
  serial_number: string;
  warranty_effective_date: string | null;
  warranty_term: string | null;
  gateway_id: string | null;
  function_id: string | null;
  driver: string | null;
  install_date: string | null;
  decommissioned_date: string | null;
  last_updated_date: string | null;
  das_connection_status: string | null;
}

interface DeviceDetailedInfoTelemetryMapping {
  telemetry_device_id: string | null;
  telemetry_device_name: string | null;
}

interface DeviceDetailedInfo {
  general_info: DeviceGeneralInfo;
  technical_details:
    | InverterDeviceTechnicalDetails
    | MeterDeviceTechnicalDetails
    | WeatherStationTechnicalDetails
    | null;
  service_detail: {
    availability?: string;
    failure_rate?: string;
    warranty_period?: 'Active' | 'End of Life';
    lifetime?: string;
    mtbr?: string;
    mttr?: string;
    next_scheduled_service_date?: Dayjs | null;
    open_repair_tickets_count?: number;
    test_interval?: string;
  };
  documents: Documents[];
  telemetry_mapping: DeviceDetailedInfoTelemetryMapping | null;
}

type UpdateDeviceGeneralInfoResponse = CreateDeviceResponse;

type UpdateDeviceTechnicalDetailsResponse = CreateDeviceResponse;

interface FileDataResponse {
  message: string;
  code: number;
}

interface FileDownload {
  download_url: string;
}

interface FilePreview {
  preview_url: string;
}

interface UrlUpload {
  filepath: string;
  upload_url: string;
}

interface TelemetrySiteDevice {
  id: string;
  name: string;
}

interface TelemetrySiteDevicesQueryResponse {
  items: TelemetrySiteDevice[] | null;
}

interface UpdateSiteInfoBaseParams {
  siteId: number;
}

interface UpdateSiteInfoSiteLevelDetailsParams extends UpdateSiteInfoBaseParams {
  section: 'site_level_details';
  data: {
    status: string | null;
    project_id: string | null;
    pvsyst: string | null;
    greenhouse_gas_offset: string | null;
    incentive_program: string | null;
    das_provider: string | null;
    das_account: string | null;
    das_username: string | null;
    das_password: string | null;
  };
}

interface UpdateSiteInfoAssetOverviewParams extends UpdateSiteInfoBaseParams {
  section: 'asset_overview';
  data: {
    battery_storage: string | null;
    mount_type: string | null;
    dc_wiring_loss: number | null;
    ac_wiring_loss: number | null;
    medium_voltage_loss: number | null;
    mv_line_loss: number | null;
  };
}

interface UpdateSiteInfoOwnershipParams extends UpdateSiteInfoBaseParams {
  section: 'ownership';
  data: {
    ownership_structure: string | null;
    hold_co: string | null;
    project_co: string | null;
    tax_credit_fund: string | null;
  };
}

interface UpdateSiteInfoTaxEquityParams extends UpdateSiteInfoBaseParams {
  section: 'tax_equity';
  data: {
    tax_equity_fund: string | null;
    tax_equity_provider: string | null;
    tax_equity_buyout_amount: number | null;
    tax_equity_buyout_date: string | null;
    tax_equity_pref_rate: number | null;
    smartsheet_data_tape: string | null;
  };
}

interface UpdateSiteInfoKeyDatesParams extends UpdateSiteInfoBaseParams {
  section: 'key_dates';
  data: {
    permission_to_operate: string | null;
    placed_in_service_date: string | null;
    financial_close_date: string | null;
  };
}

interface UpdateSiteInfoOnMParams extends UpdateSiteInfoBaseParams {
  section: 'o_and_m';
  data: {
    om_address: string | null;
    om_contact_name: string | null;
    om_contact_email: string | null;
    om_contact_phone: string | null;
    o_and_m_rate: number | null;
  };
}

interface UpdateSiteInfoInterconnectionUtilityProviderParams extends UpdateSiteInfoBaseParams {
  section: 'interconnection';
  data: {
    iut_address: string | null;
    iut_contact_name: string | null;
    iut_contact_email: string | null;
    iut_contact_phone: string | null;
    utility_rate: string | null;
  };
}

interface UpdateSiteInfoEPCContractorParams extends UpdateSiteInfoBaseParams {
  section: 'epc_contractor';
  data: {
    epc_address: string | null;
    epc_contact_name: string | null;
    epc_contact_email: string | null;
    epc_contact_phone: string | null;
  };
}

interface UpdateSiteInfoCommunitySolarManagerParams extends UpdateSiteInfoBaseParams {
  section: 'community_solar_manager';
  data: {
    csm_provider: string | null;
    csm_address: string | null;
    csm_contact_name: string | null;
    csm_contact_email: string | null;
    csm_contact_phone: string | null;
    csm_fee: number | null;
    escalator: number | null;
    escalator_effective: string | null;
  };
}

interface UpdateSiteInfoInsuranceProviderParams extends UpdateSiteInfoBaseParams {
  section: 'insurance_provider';
  data: {
    insurance_provider: string | null;
    insurance_address: string | null;
  };
}

interface UpdateSiteInfoSiteLeaseParams extends UpdateSiteInfoBaseParams {
  section: 'site_lease';
  data: {
    rent_escalator: string | null;
    payment_due_date: string | null;
    lease_payment_method: string | null;
    lease_payment_frequency: string | null;
    landlord_contact_phone: string | null;
  };
}

interface UpdateSiteInfoVegetationVendorParams extends UpdateSiteInfoBaseParams {
  section: 'vegetation_vendor';
  data: {
    vv_provider: string | null;
    vv_address: string | null;
    vv_contact_name: string | null;
    vv_contact_phone: string | null;
    vv_contact_email: string | null;
  };
}

interface UpdateSiteInfoOfftakerParams extends UpdateSiteInfoBaseParams {
  section: 'offtaker';
  data: {
    offtaker_name: string | null;
    offtaker_type: string | null;
    credit_rating: string | null;
    rating_agency: string | null;
    date_of_rating: string | null;
  };
}

interface UpdateSiteInfoComplianceParams extends UpdateSiteInfoBaseParams {
  section: 'compliance';
  data: {
    entity: string | null;
    bank: string | null;
    report_due_date: string | null;
    fiscal_year_end: string | null;
    tax_return_deadline: string | null;
  };
}

type UpdateSiteInfoParams =
  | UpdateSiteInfoSiteLevelDetailsParams
  | UpdateSiteInfoAssetOverviewParams
  | UpdateSiteInfoOwnershipParams
  | UpdateSiteInfoTaxEquityParams
  | UpdateSiteInfoKeyDatesParams
  | UpdateSiteInfoOnMParams
  | UpdateSiteInfoInterconnectionUtilityProviderParams
  | UpdateSiteInfoEPCContractorParams
  | UpdateSiteInfoCommunitySolarManagerParams
  | UpdateSiteInfoInsuranceProviderParams
  | UpdateSiteInfoSiteLeaseParams
  | UpdateSiteInfoVegetationVendorParams
  | UpdateSiteInfoOfftakerParams
  | UpdateSiteInfoComplianceParams;

interface UpdateSiteInfoResponse {
  message: string;
  code: number;
}

export const buildAssetManagementApi = (httpClient: AxiosInstance) => {
  const companies = async (params: Params): Promise<Companies> => {
    const response = await httpClient.get<Companies>('/api/companies/', { params });
    return response.data;
  };

  const sites = async (params: Params): Promise<Sites> => {
    const response = await httpClient.get<Sites>('/api/sites/', { params });
    return response.data;
  };

  const createSite = async (attributes: CreateSiteAttributes): Promise<CreateSiteResponse> => {
    const response = await httpClient.post<CreateSiteResponse>('/api/sites/', attributes);
    return response.data;
  };

  const updateSite = async (id: number | undefined, attributes: CreateSiteAttributes): Promise<CreateSiteResponse> => {
    const response = await httpClient.put<CreateSiteResponse>(`/api/sites/${id}`, attributes);
    return response.data;
  };

  const contractors = async (params: Params): Promise<Contractors> => {
    const response = await httpClient.get<Contractors>('/api/contractors/', { params });
    return response.data;
  };

  const getCompanyById = async (companyId: number): Promise<CompanyDetails> => {
    const response = await httpClient.get<CompanyDetails>(`/api/companies/${companyId}`);
    return response.data;
  };

  const getSiteById = async (siteId: number): Promise<SiteDetailedInfo> => {
    const response = await httpClient.get<SiteDetailedInfo>(`/api/sites/${siteId}`);
    return response.data;
  };

  const createDevice = async (siteId: number, attributes: CreateDeviceAttributes): Promise<CreateDeviceResponse> => {
    const response = await httpClient.post<CreateDeviceResponse>(`/api/sites/${siteId}/devices/`, attributes);
    return response.data;
  };

  const siteInfo = async (siteId: number): Promise<DetailedSiteInfo> => {
    const response = await httpClient.get<DetailedSiteInfo>(`/api/sites/${siteId}/details`);
    return response.data;
  };

  const updateSiteInfo = async (params: UpdateSiteInfoParams): Promise<UpdateSiteInfoResponse> => {
    const response = await httpClient.put(`/api/sites/${params.siteId}/details`, params.data, {
      params: { section_name: params.section }
    });
    return response.data;
  };

  const devices = async (siteId: number, params: Params): Promise<Devices> => {
    const response = await httpClient.get<Devices>(`/api/sites/${siteId}/devices/`, { params });
    return response.data;
  };

  const deviceById = async (siteId: number, deviceId: number): Promise<DeviceDetailedInfo> => {
    const response = await httpClient.get<DeviceDetailedInfo>(`/api/sites/${siteId}/devices/${deviceId}`);
    return response.data;
  };

  const updateDeviceGeneralInfo = async (
    params: UpdateDeviceGeneralInfoParams
  ): Promise<UpdateDeviceGeneralInfoResponse> => {
    const { siteId, deviceId, attributes } = params;
    const response = await httpClient.put(`/api/sites/${siteId}/devices/${deviceId}/general-info`, attributes);
    return response.data;
  };

  const updateServiceDetail = async (
    device_id: number,
    site_id: number,
    data: ServiceDetailAttributes
  ): Promise<CreateSiteResponse> => {
    const response = await httpClient.put<CreateSiteResponse>(
      `/api/sites/${site_id}/devices/${device_id}/service-details`,
      data
    );

    return response.data;
  };

  const updateTechnicalDetails = async (
    device_id: number,
    site_id: number,
    data: TechnicalDetailAttributes
  ): Promise<UpdateDeviceTechnicalDetailsResponse> => {
    const response = await httpClient.put<UpdateDeviceTechnicalDetailsResponse>(
      `/api/sites/${site_id}/devices/${device_id}/technical-details`,
      data
    );

    return response.data;
  };

  const deleteFile = async (siteId: number, deviceId: number, fileId: number): Promise<FileDataResponse> => {
    const response = await httpClient.delete<FileDataResponse>(
      `/api/sites/${siteId}/devices/${deviceId}/documents/${fileId}`
    );
    return response.data;
  };

  const downloadFile = async (siteId: number, deviceId: number, fileId: number): Promise<FileDownload> => {
    const response = await httpClient.get<FileDownload>(
      `/api/sites/${siteId}/devices/${deviceId}/documents/${fileId}/download-url`
    );
    return response.data;
  };

  const previewFile = async (siteId: number, deviceId: number, fileId: number): Promise<FilePreview> => {
    const response = await httpClient.get<FilePreview>(
      `/api/sites/${siteId}/devices/${deviceId}/documents/${fileId}/file-preview-url/`
    );
    return response.data;
  };

  const uploadUrl = async (filename: string, siteId: number, deviceId: number): Promise<UrlUpload> => {
    const response = await httpClient.post<UrlUpload>(`/api/sites/${siteId}/devices/${deviceId}/documents/upload-url`, {
      filename: filename
    });
    return response?.data;
  };

  const uploadFile = async (fileData: File, uploadUrl: string): Promise<any> => {
    const contentType =
      fileData.type.includes('pdf') || fileData.type.includes('office') || fileData.type.includes('word')
        ? 'application/octet-stream'
        : fileData.type;

    return axios.put(uploadUrl, fileData, {
      headers: {
        'Content-Type': contentType
      }
    });
  };

  const uploadConfirm = async (
    filepath: string,
    filename: string,
    category: Category,
    siteId: number,
    deviceId: number
  ): Promise<FileDataResponse> => {
    const response = await httpClient.post<FileDataResponse>(
      `/api/sites/${siteId}/devices/${deviceId}/documents/track-uploaded-document`,
      { filepath: filepath, filename: filename, category: category }
    );
    return response?.data;
  };

  const telemetrySiteDevices = async (siteId: number): Promise<TelemetrySiteDevicesQueryResponse> => {
    const response = await httpClient.get<TelemetrySiteDevicesQueryResponse>(`/api/telemetry/sites/${siteId}/devices`);
    return response.data;
  };

  const updateTelemetrySiteDevices = async (siteId: number, deviceId: number): Promise<FileDataResponse> => {
    const response = await httpClient.put<FileDataResponse>(
      `/api/sites/${siteId}/devices/${deviceId}/telemetry-details`
    );
    return response.data;
  };

  return Object.freeze({
    companies,
    sites,
    devices,
    createSite,
    contractors,
    getCompanyById,
    getSiteById,
    createDevice,
    siteInfo,
    deviceById,
    updateSite,
    updateDeviceGeneralInfo,
    updateServiceDetail,
    updateTechnicalDetails,
    deleteFile,
    downloadFile,
    previewFile,
    uploadUrl,
    uploadFile,
    uploadConfirm,
    telemetrySiteDevices,
    updateSiteInfo,
    updateTelemetrySiteDevices
  });
};

export type {
  Companies,
  Sites,
  SiteDetailedInfo,
  CreateSiteAttributes,
  CompanyDetails,
  DeviceDetailedInfo,
  ServiceDetailCardFormFields,
  FileDataResponse,
  UrlUpload,
  Category,
  InverterFormFields,
  InverterDeviceTechnicalDetails,
  TechnicalDetailAttributes,
  ModuleDeviceTechnicalDetails,
  ModuleFormFields,
  ModemDeviceTechnicalDetails,
  ModemFormFields,
  RackMountDeviceTechnicalDetails,
  RackMountFormFields,
  CameraDeviceTechnicalDetails,
  CameraFormFields,
  MeterDeviceTechnicalDetails,
  TransformerDeviceTechnicalDetails,
  NetworkConnectionDeviceTechnicalDetails,
  BatteryDeviceTechnicalDetails,
  CombinerBoxDeviceTechnicalDetails,
  WeatherStationTechnicalDetails
};

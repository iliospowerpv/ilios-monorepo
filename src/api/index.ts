import { httpClient, tokenManager } from './http-client';
import { buildUserApi } from './user';
import { buildAssetManagementApi } from './asset-management';
import { buildCompaniesApi } from './companies';
import { buildRecoveryApi } from './password-recovery';
import { buildMyCompanyApi } from './my-company';
import { buildSettingsApi } from './settings';
import { buildOperationsAndMaintenanceApi } from './operations-and-maintenance';
import { buildDueDiligenceApi } from './due-diligence';
import { buildTaskManagementApi } from './task-management';
import { buildAuditLogApi } from './audit-log';
import { buildDashboardApi } from './dashboard';
import { buildSecurityApi } from './security';
import { buildConnectionsApi } from './connections';
import { buildInvestorDashboardApi } from './investor-dashboard';
import { buildBreadcrumbsApi } from './breadcrumbs';
import { buildReportsApi } from './reports';

export const ApiClient = Object.freeze({
  _tokenManager: tokenManager,
  user: buildUserApi(httpClient),
  assetManagement: buildAssetManagementApi(httpClient),
  companies: buildCompaniesApi(httpClient),
  passwordRecovery: buildRecoveryApi(httpClient),
  myCompany: buildMyCompanyApi(httpClient),
  settings: buildSettingsApi(httpClient),
  operationsAndMaintenance: buildOperationsAndMaintenanceApi(httpClient),
  dueDiligence: buildDueDiligenceApi(httpClient),
  taskManagement: buildTaskManagementApi(httpClient),
  auditLog: buildAuditLogApi(httpClient),
  dashboard: buildDashboardApi(httpClient),
  security: buildSecurityApi(httpClient),
  connections: buildConnectionsApi(httpClient),
  investorDashboard: buildInvestorDashboardApi(httpClient),
  breadcrumbs: buildBreadcrumbsApi(httpClient),
  reports: buildReportsApi(httpClient)
});

export type {
  UserAuth,
  UserLoginData,
  UserLogoutData,
  Roles,
  Role,
  ResetPasswordData,
  CreateUserAttributes,
  CreateUserResponse,
  Users,
  User,
  Params,
  UserDetailedInfo,
  EditUserInfoInputPartial
} from './user';

export type {
  CreateSiteAttributes,
  SiteDetailedInfo,
  DeviceDetailedInfo,
  Category,
  InverterFormFields,
  InverterDeviceTechnicalDetails,
  TechnicalDetailAttributes,
  ModuleFormFields,
  ModuleDeviceTechnicalDetails,
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
} from './asset-management';

export type {
  FileItem,
  FileDataResponse,
  UrlUpload,
  AgreementType,
  AgreementTypes,
  AgreementTerm,
  AgreementTerms,
  DiligenceDetailsList,
  DiligenceItem,
  DiligenceDocument
} from './due-diligence';

export type { CompanySite, CompanySites, CompanyAttributes, ContractorCompany } from './companies';

export type { Recovery, ResetRequestData, EmailTokenData, ResetSetupData } from './password-recovery';

export type { CompanyDetails, Sites } from './my-company';

export type { SettingsSites } from './settings';

export type { OMCompanyDetails, OMSiteDetails, OMDeviceDetails } from './operations-and-maintenance';

export type { Tasks, Boards, Status, Statuses, TaskType, Assignee, Creator } from './task-management';

export type { AuditLog, AuditLogs } from './audit-log';

export type { DashboardTasks, DashboardTask, Notification, Notifications } from './dashboard';

export type { SecurityCamera, SecurityCameras } from './security';

export type { GetBreadcrumbsParams, GetBreadcrumbsResponse } from './breadcrumbs';

export type {
  Connection,
  Connections,
  ConnectionResponse,
  CreateSiteMappingAttributes,
  SiteMapping
} from './connections';

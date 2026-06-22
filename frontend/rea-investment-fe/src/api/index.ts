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
import { buildAccessibleEntitiesApi } from './accessible-entities';
import { buildWorkspaceApi } from './workspace';
import { buildAdminApi } from './admin';
import { createContactsApi } from './contacts';
import { createEntitiesApi } from './entities';
import { financeIntegrations, financeData } from './financeIntegrations';
import { buildProjectImportApi } from './project-import';
import { buildTelemetryV2Api } from './telemetryV2';
import { buildReconciliationApi } from './reconciliation';
import { buildAssumptionsApi } from './assumptions';

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
  reports: buildReportsApi(httpClient),
  accessibleEntities: buildAccessibleEntitiesApi(httpClient),
  workspace: buildWorkspaceApi(httpClient),
  admin: buildAdminApi(httpClient),
  contacts: createContactsApi(httpClient),
  ...createEntitiesApi(httpClient),
  financeIntegrations,
  financeData,
  projectImport: buildProjectImportApi(httpClient),
  telemetryV2: buildTelemetryV2Api(httpClient),
  reconciliation: buildReconciliationApi(httpClient),
  assumptions: buildAssumptionsApi(httpClient)
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
  DiligenceDocument,
  ParseStateSummary,
  ParseState,
  ParseNextAction,
  NoUsableFieldsReason
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

export type { AccessibleCompany, AccessibleProject, AccessibleEntitiesResponse } from './accessible-entities';

export type {
  WorkspaceResponse,
  WorkspaceSummary,
  WorkspaceCompany,
  CompanyMember,
  AddMemberRequest,
  UpdateMemberRequest,
  PortfolioMember,
  PortfolioMembersResponse,
  AddPortfolioMemberRequest,
  ProjectMember,
  ProjectMembersResponse,
  AddProjectMemberRequest,
  RoleProfile
} from './workspace';

export type {
  AccessHealthResponse,
  ValidationResult,
  ValidationIssue,
  RepairResult,
  CanonicalField,
  DocumentType,
  SchemaVersionField,
  SchemaVersion,
  PromptTemplate
} from './admin';

export type {
  Contact,
  ContactCreate,
  ContactUpdate,
  ContactListResponse,
  ContactsQueryParams,
  ContactScopeType
} from './contacts';

export type {
  EntityType,
  EntityRelationshipRole,
  DealEntityRole,
  ProjectEntity,
  ProjectEntityCreate,
  ProjectEntityUpdate,
  ProjectEntityListResponse,
  EntityRelationship,
  EntityRelationshipCreate,
  EntityRelationshipUpdate,
  EntityRelationshipListResponse,
  DealEntityAssignment,
  DealEntityAssignmentCreate,
  DealEntityAssignmentUpdate,
  DealEntityAssignmentListResponse,
  EntityListParams,
  EntitiesApi
} from './entities';

export type {
  FinanceIntegration,
  FinanceProviderInfo,
  FinanceIntegrationsListResponse,
  FinanceIntegrationCredentials,
  FinanceIntegrationCreatePayload,
  FinanceIntegrationUpdatePayload,
  FinanceIntegrationTestResponse
} from './financeIntegrations';

export type {
  ReconciliationValue,
  ReconciliationStatus,
  ReconciliationCategory,
  ReconciliationBaselineTarget,
  ReconciliationWarning,
  ReconciliationRow,
  ReconciliationReadiness,
  TelemetryReality,
  SiteReconciliationResponse
} from './reconciliation';

export type {
  PromotionChangeType,
  PromotionDiffChange,
  PromotionDiffSummary,
  PromotionDiff,
  ProjectFact,
  ActiveFactsResponse as AssumptionsActiveFactsResponse,
  PromoteVersionPayload,
  PromoteVersionResponse,
  PromotionHistoryItem,
  PromotionHistoryResponse
} from './assumptions';

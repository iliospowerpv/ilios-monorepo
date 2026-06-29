import React from 'react';
import { Route, createBrowserRouter, createRoutesFromElements, Navigate, useParams } from 'react-router-dom';
// Providers
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { ThemeModeProvider } from './contexts/theme/theme';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from 'react-router-dom';
import { BaseLayout } from './components/layout/BaseLayout/BaseLayout';
import { AuthLayout } from './components/layout/AuthLayout/AuthLayout';
import { AuthProvider, useAuth } from './contexts/auth/auth';
import { NotificationsProvider } from './contexts/notifications/notifications';
import { ActionProcessorsProvider } from './contexts/action-processor/action-processor';
import { withAuthControl } from './utils/loaders';

import Login from './pages/Login/Login';
import PasswordResetRequest from './pages/PasswordResetRequest/PasswordResetRequest';
import PasswordResetNotification from './pages/PasswordResetNotification/PasswordResetNotification';
import PasswordReset from './pages/PasswordReset/PasswordReset';
import PasswordResetSuccess from './pages/PasswordResetSuccess/PasswordResetSuccess';
import PasswordResetInvalid from './pages/PasswordResetInvalid/PasswordResetInvalid';
import SignUp from './pages/SignUp/SignUp';
import Index from './pages/Index/Index';
import { AccountSettings } from './pages/Account';
import { SecuritySettings } from './pages/Security';
import { HelpResources } from './pages/Help';
import { PortfolioView, CompaniesPickerView, ProjectsPickerView } from './pages/Hierarchy';
import { TelemetryPage, createTelemetryHandle, TelemetryRedirect } from './pages/Telemetry';
import { ScopedModuleRoute } from './components/layout/ScopedModuleRoute';
import { DeprecatedRouteRedirect } from './components/common/DeprecatedRouteRedirect';

import {
  CompanyTask as PHCompanyTask,
  Root as PHRoot,
  CompanyDetails as PHCompanyDetails,
  SiteDetails as PHSiteDetails,
  AddDevice as PHAddDevice,
  DeviceDetails as PHDeviceDetails,
  ModuleContainer as PHModuleContainer
} from './modules/project-hub';
import {
  AllCompanies as OMAllCompanies,
  CompanyDetails as OMCompanyDetails,
  SiteDetails as OMSiteDetails,
  createCompanyDetailsHandle,
  createCompanyDetailsLoader,
  CompanyTask as OMCompanyTask,
  ModuleContainer as OMModuleContainer
} from './modules/operations-and-maintenance';
import { SettingsPage, HealthChecksPage } from './modules/settings';
import {
  DueDiligencePage as DPDiligencePage,
  SitesPage as DPSitesPage,
  ModuleContainer as DDModuleContainer
} from './modules/due-diligence';
import { ErrorLayout } from './components/layout/ErrorLayout/ErrorLayout';
import { PortfolioPage, ModuleContainer as PortfolioModuleContainer } from './modules/my-portfolio';
import { AllReports, ModuleContainer as ReportsModuleContainer } from './modules/reports';
import {
  FinanceLanding,
  FinanceHome,
  SiteFinance,
  ModuleContainer as FinanceModuleContainer,
  createFinanceLandingHandle,
  createFinanceHomeHandle,
  createSiteFinanceHandle
} from './modules/finance';
import {
  SalesHome as AcquisitionsHome,
  SalesModuleContainer as AcquisitionsModuleContainer,
  createSalesHomeHandle as createAcquisitionsHomeHandle,
  DealDetail
} from './modules/acquisitions';
import { HomePage, createHomeHandle } from './modules/home/pages';
import { ModuleContainer as HomeModuleContainer } from './modules/home';
import {
  OnboardingPage,
  createOnboardingHandle,
  ModuleContainer as OnboardingModuleContainer
} from './modules/onboarding';
import {
  PortfolioAdminModuleContainer,
  PortfolioLevelPage,
  createPortfolioLevelHandle,
  CompanyLevelPage,
  createCompanyLevelHandle,
  ProjectLevelPage,
  createProjectLevelHandle
} from './modules/portfolio-admin';
import {
  AddCompanyWorkflowPage,
  AddSiteWorkflowPage,
  WorkflowDashboardPage,
  WorkflowRunPage,
  GenericWorkflowStartPage,
  OnboardingOrchestratorPage
} from './modules/workflows';

const ProjectLandingRedirect: React.FC = () => {
  const { projectId } = useParams();
  return <Navigate to={`/project-hub/projects/${projectId}`} replace />;
};

const CompanyRedirect: React.FC = () => {
  const { companyId } = useParams();
  return <Navigate to={`/project-hub/companies/${companyId}`} replace />;
};

const queryClient = new QueryClient();

const AdminType = {
  system: 'is_system_user',
  full: 'company_admin_full',
  view: 'company_view'
};

type ProtectedRouteProps = {
  element: React.ReactElement;
  permission: string[];
};

const ProtectedSettingsRoute = ({ element, permission }: ProtectedRouteProps) => {
  const { isAuthenticated, user } = useAuth();

  if (isAuthenticated) {
    const isSystem = permission.some(perm => perm === 'is_system_user');
    const isCompanyAdmin = permission.some(perm => perm === 'company_admin_full');
    if (isSystem && user?.is_system_user) {
      return element;
    } else if (isCompanyAdmin && user?.role?.permissions?.['Settings Page']?.view) {
      return element;
    }
  }

  return <Navigate to="/" replace />;
};

const router = createBrowserRouter(
  createRoutesFromElements(
    <Route>
      <Route element={<BaseLayout />} errorElement={<ErrorLayout />}>
        <Route index element={<Index />} />
        <Route path="/account" element={<AccountSettings />} />
        <Route path="/security" element={<SecuritySettings />} />
        <Route path="/help" element={<HelpResources />} />
        <Route path="/portfolio" element={<PortfolioView />} />

        {/* Home - Unified landing page (combines Dashboard + Workspace) */}
        <Route path="/home" element={<HomeModuleContainer />}>
          <Route index handle={createHomeHandle()} element={<HomePage />} />
        </Route>

        {/* Onboarding wizard */}
        <Route path="/onboarding" element={<OnboardingModuleContainer />}>
          <Route index handle={createOnboardingHandle()} element={<OnboardingPage />} />
        </Route>

        {/* Native Workflow Engine — dashboard, onboarding orchestrator, and single workflows */}
        <Route path="/workflows" element={<WorkflowDashboardPage />} />
        <Route path="/workflows/onboarding" element={<OnboardingOrchestratorPage />} />
        <Route path="/workflows/run/:runId" element={<WorkflowRunPage />} />
        <Route path="/workflows/add-company" element={<AddCompanyWorkflowPage />} />
        <Route path="/workflows/add-site" element={<AddSiteWorkflowPage />} />
        <Route path="/workflows/start/:workflowId" element={<GenericWorkflowStartPage />} />

        {/* Legacy redirects to Home */}
        <Route path="/workspace" element={<Navigate to="/home" replace />} />
        <Route path="/workspace/*" element={<Navigate to="/home" replace />} />

        {/* Portfolio Admin - Three-tier hierarchy for administration */}
        <Route path="/portfolio-admin" element={<PortfolioAdminModuleContainer />}>
          <Route index handle={createPortfolioLevelHandle()} element={<PortfolioLevelPage />} />
          <Route path="companies/:companyId" handle={createCompanyLevelHandle()} element={<CompanyLevelPage />} />
          <Route path="projects/:projectId" handle={createProjectLevelHandle()} element={<ProjectLevelPage />} />
        </Route>

        {/* Legacy Admin redirects to Settings Health Checks */}
        <Route path="/admin/access-health" element={<Navigate to="/settings/health-checks" replace />} />

        {/* Legacy Company Admin redirects to Portfolio Admin */}
        <Route path="/company-admin" element={<Navigate to="/portfolio-admin" replace />} />
        <Route path="/companies" element={<CompaniesPickerView />} />
        <Route path="/companies/:companyId" element={<CompanyRedirect />} />
        <Route path="/projects" element={<ProjectsPickerView />} />
        <Route path="/projects/:projectId" element={<ProjectLandingRedirect />} />
        <Route path="/projects/:projectId/telemetry" handle={createTelemetryHandle()} element={<TelemetryPage />} />

        {/* Dashboard redirects to Home (deprecated) */}
        <Route path="/dashboard" element={<Navigate to="/home" replace />} />
        <Route path="/dashboard/*" element={<Navigate to="/home" replace />} />
        {/* Legacy redirect: /my-portfolio → /portfolio */}
        <Route path="/my-portfolio/*" element={<Navigate to="/portfolio" replace />} />
        {/* Portfolio Module with Scoped Lens Routes */}
        <Route path="/portfolio" element={<PortfolioModuleContainer />}>
          <Route
            path="scope/portfolio"
            element={
              <ScopedModuleRoute scope="portfolio">
                <PortfolioPage.Component />
              </ScopedModuleRoute>
            }
          />
          <Route
            path="scope/company/:companyId"
            element={
              <ScopedModuleRoute scope="company">
                <PortfolioPage.Component />
              </ScopedModuleRoute>
            }
          />
          <Route
            path="scope/project/:projectId"
            element={
              <ScopedModuleRoute scope="project">
                <PortfolioPage.Component />
              </ScopedModuleRoute>
            }
          />
          <Route index handle={PortfolioPage.createHandle()} element={<PortfolioPage.Component />} />
        </Route>
        {/* Reports Module with Scoped Lens Routes */}
        <Route path="/reports" element={<ReportsModuleContainer />}>
          <Route
            path="scope/portfolio"
            element={
              <ScopedModuleRoute scope="portfolio">
                <AllReports.Component />
              </ScopedModuleRoute>
            }
          />
          <Route
            path="scope/company/:companyId"
            element={
              <ScopedModuleRoute scope="company">
                <AllReports.Component />
              </ScopedModuleRoute>
            }
          />
          <Route
            path="scope/project/:projectId"
            element={
              <ScopedModuleRoute scope="project">
                <AllReports.Component />
              </ScopedModuleRoute>
            }
          />
        </Route>
        <Route path="/reports" element={<ReportsModuleContainer />}>
          <Route index handle={AllReports.createHandle()} element={<AllReports.Component />} />
        </Route>
        {/* Finance Module with Scoped Lens Routes */}
        <Route path="/finance" element={<FinanceModuleContainer />}>
          <Route
            path="scope/portfolio"
            element={
              <ScopedModuleRoute scope="portfolio">
                <FinanceLanding />
              </ScopedModuleRoute>
            }
          />
          <Route
            path="scope/company/:companyId"
            element={
              <ScopedModuleRoute scope="company">
                <FinanceHome />
              </ScopedModuleRoute>
            }
          />
          <Route
            path="scope/project/:projectId"
            element={
              <ScopedModuleRoute scope="project">
                <SiteFinance />
              </ScopedModuleRoute>
            }
          />
        </Route>
        <Route path="/finance" element={<FinanceModuleContainer />}>
          <Route index handle={createFinanceLandingHandle()} element={<FinanceLanding />} />
          <Route path="companies/:companyId" handle={createFinanceHomeHandle(queryClient)} element={<FinanceHome />} />
          <Route
            path="companies/:companyId/sites/:siteId"
            handle={createSiteFinanceHandle(queryClient)}
            element={<SiteFinance />}
          />
        </Route>
        {/* Acquisitions Module (formerly Sales) */}
        <Route path="/acquisitions" element={<AcquisitionsModuleContainer />}>
          <Route
            path="scope/portfolio"
            element={
              <ScopedModuleRoute scope="portfolio">
                <AcquisitionsHome />
              </ScopedModuleRoute>
            }
          />
          <Route
            path="scope/company/:companyId"
            element={
              <ScopedModuleRoute scope="company">
                <AcquisitionsHome />
              </ScopedModuleRoute>
            }
          />
          <Route
            path="scope/project/:projectId"
            element={
              <ScopedModuleRoute scope="project">
                <AcquisitionsHome />
              </ScopedModuleRoute>
            }
          />
        </Route>
        <Route path="/acquisitions" element={<AcquisitionsModuleContainer />}>
          <Route index handle={createAcquisitionsHomeHandle(queryClient)} element={<AcquisitionsHome />} />
          <Route path="deal/:dealId" element={<DealDetail />} />
        </Route>
        {/* Due Diligence Module with Scoped Lens Routes */}
        <Route path="/due-diligence" element={<DDModuleContainer />}>
          <Route
            path="scope/portfolio"
            element={
              <ScopedModuleRoute scope="portfolio">
                <DPDiligencePage.Component />
              </ScopedModuleRoute>
            }
          />
          <Route
            path="scope/company/:companyId"
            element={
              <ScopedModuleRoute scope="company">
                <DPDiligencePage.Component />
              </ScopedModuleRoute>
            }
          />
          <Route
            path="scope/project/:projectId"
            element={
              <ScopedModuleRoute scope="project">
                <DPDiligencePage.Component />
              </ScopedModuleRoute>
            }
          />
        </Route>
        <Route path="/due-diligence" element={<DDModuleContainer />}>
          <Route index handle={DPDiligencePage.createHandle()} element={<DPDiligencePage.Component />} />
          <Route
            path="/due-diligence/companies/:companyId/sites"
            handle={DPSitesPage.createHandle(queryClient)}
            loader={DPSitesPage.createLoader(queryClient)}
            element={<DPSitesPage.Component />}
          />
          {/* Legacy site routes - redirect to canonical Project Hub Data Room tab */}
          <Route
            path="/due-diligence/companies/:companyId/sites/:siteId"
            element={<DeprecatedRouteRedirect targetTab="data-room" />}
          />
          <Route
            path="/due-diligence/companies/:companyId/sites/:siteId/overview"
            element={<DeprecatedRouteRedirect targetTab="overview" />}
          />
          <Route
            path="/due-diligence/companies/:companyId/sites/:siteId/due-diligence"
            element={<DeprecatedRouteRedirect targetTab="data-room" />}
          />
          <Route
            path="/due-diligence/companies/:companyId/sites/:siteId/due-diligence/:documentId"
            element={<DeprecatedRouteRedirect targetTab="data-room" />}
          />
        </Route>
        {/* O&M Module with Scoped Lens Routes */}
        <Route path="/operations-and-maintenance" element={<OMModuleContainer />}>
          <Route
            path="scope/portfolio"
            element={
              <ScopedModuleRoute scope="portfolio">
                <OMAllCompanies.Component />
              </ScopedModuleRoute>
            }
          />
          <Route
            path="scope/company/:companyId"
            element={
              <ScopedModuleRoute scope="company">
                <OMCompanyDetails />
              </ScopedModuleRoute>
            }
          />
          <Route
            path="scope/project/:projectId"
            element={
              <ScopedModuleRoute scope="project">
                <OMSiteDetails />
              </ScopedModuleRoute>
            }
          />
          <Route
            path="scope/project/:projectId/telemetry"
            element={
              <ScopedModuleRoute scope="project">
                <TelemetryPage />
              </ScopedModuleRoute>
            }
          />
        </Route>
        <Route path="/operations-and-maintenance" element={<OMModuleContainer />}>
          <Route index handle={OMAllCompanies.createHandle()} element={<OMAllCompanies.Component />} />
          <Route path="companies" handle={OMAllCompanies.createHandle()} element={<OMAllCompanies.Component />} />
          <Route
            path="companies/:companyId"
            handle={createCompanyDetailsHandle(queryClient)}
            loader={withAuthControl(createCompanyDetailsLoader(queryClient))}
            element={<OMCompanyDetails />}
          />
          <Route
            path="companies/:companyId/overview"
            handle={createCompanyDetailsHandle(queryClient)}
            loader={withAuthControl(createCompanyDetailsLoader(queryClient))}
            element={<OMCompanyDetails tabId="overview" />}
          />
          <Route
            path="companies/:companyId/sites"
            handle={createCompanyDetailsHandle(queryClient)}
            loader={withAuthControl(createCompanyDetailsLoader(queryClient))}
            element={<OMCompanyDetails tabId="sites" />}
          />
          <Route
            path="companies/:companyId/alerts"
            handle={createCompanyDetailsHandle(queryClient)}
            loader={withAuthControl(createCompanyDetailsLoader(queryClient))}
            element={<OMCompanyDetails tabId="alerts" />}
          />
          <Route
            path="companies/:companyId/tasks"
            handle={createCompanyDetailsHandle(queryClient)}
            loader={withAuthControl(createCompanyDetailsLoader(queryClient))}
            element={<OMCompanyDetails tabId="tasks" />}
          />
          <Route
            path="companies/:companyId/tasks/:taskId"
            handle={OMCompanyTask.createHandle(queryClient)}
            loader={withAuthControl(OMCompanyTask.createLoader(queryClient))}
            element={<OMCompanyTask.Component />}
          />
          {/* Legacy site routes - redirect to canonical Project Hub O&M tab */}
          <Route path="companies/:companyId/sites/:siteId" element={<DeprecatedRouteRedirect targetTab="om" />} />
          <Route
            path="companies/:companyId/sites/:siteId/overview"
            element={<DeprecatedRouteRedirect targetTab="overview" />}
          />
          <Route
            path="companies/:companyId/sites/:siteId/devices"
            element={<DeprecatedRouteRedirect targetTab="om" />}
          />
          <Route
            path="companies/:companyId/sites/:siteId/alerts"
            element={<DeprecatedRouteRedirect targetTab="om" />}
          />
          <Route
            path="companies/:companyId/sites/:siteId/security"
            element={<DeprecatedRouteRedirect targetTab="om" />}
          />
          <Route
            path="companies/:companyId/sites/:siteId/tasks"
            element={<DeprecatedRouteRedirect targetTab="tasks" />}
          />
          <Route
            path="companies/:companyId/sites/:siteId/tasks/:taskId"
            element={<DeprecatedRouteRedirect targetTab="tasks" />}
          />
          {/*TODO: Device for O&M*/}
          {/*<Route*/}
          {/*  path="companies/:companyId/sites/:siteId/device/:deviceId"*/}
          {/*  handle={createDeviceDetailsHandle()}*/}
          {/*  loader={withAuthControl(createDeviceDetailsLoader(queryClient))}*/}
          {/*  element={<OMDeviceDetails />}*/}
          {/*/>*/}
          {/*<Route*/}
          {/*  path="companies/:companyId/sites/:siteId/device/:deviceId/overview"*/}
          {/*  handle={createDeviceDetailsHandle()}*/}
          {/*  loader={withAuthControl(createDeviceDetailsLoader(queryClient))}*/}
          {/*  element={<OMDeviceDetails tabId="overview" />}*/}
          {/*/>*/}
          {/*<Route*/}
          {/*  path="companies/:companyId/sites/:siteId/device/:deviceId/alerts"*/}
          {/*  handle={createDeviceDetailsHandle()}*/}
          {/*  loader={withAuthControl(createDeviceDetailsLoader(queryClient))}*/}
          {/*  element={<OMDeviceDetails tabId="alerts" />}*/}
          {/*/>*/}
        </Route>
        {/* Project Hub Module (formerly Asset Management) with Scoped Lens Routes */}
        <Route path="/project-hub" element={<PHModuleContainer />}>
          <Route
            path="scope/portfolio"
            element={
              <ScopedModuleRoute scope="portfolio">
                <PHRoot.Component />
              </ScopedModuleRoute>
            }
          />
          <Route
            path="scope/company/:companyId"
            element={
              <ScopedModuleRoute scope="company">
                <PHCompanyDetails.Component />
              </ScopedModuleRoute>
            }
          />
          <Route
            path="scope/project/:projectId"
            element={
              <ScopedModuleRoute scope="project">
                <PHSiteDetails.Component />
              </ScopedModuleRoute>
            }
          />
        </Route>
        <Route path="/project-hub" element={<PHModuleContainer />}>
          <Route path="/project-hub" handle={PHRoot.createHandle()} element={<PHRoot.Component />} />
          <Route
            path="/project-hub/overview"
            handle={PHRoot.createHandle()}
            element={<PHRoot.Component tabId="overview" />}
          />
          <Route
            path="/project-hub/sites"
            handle={PHRoot.createHandle()}
            element={<PHRoot.Component tabId="sites" />}
          />
          <Route
            path="/project-hub/companies/:companyId"
            handle={PHCompanyDetails.createHandle(queryClient)}
            loader={withAuthControl(PHCompanyDetails.createLoader(queryClient))}
            element={<PHCompanyDetails.Component />}
          />
          <Route
            path="/project-hub/companies/:companyId/overview"
            handle={PHCompanyDetails.createHandle(queryClient)}
            loader={withAuthControl(PHCompanyDetails.createLoader(queryClient))}
            element={<PHCompanyDetails.Component tabId="overview" />}
          />
          <Route
            path="/project-hub/companies/:companyId/sites"
            handle={PHCompanyDetails.createHandle(queryClient)}
            loader={withAuthControl(PHCompanyDetails.createLoader(queryClient))}
            element={<PHCompanyDetails.Component tabId="sites" />}
          />
          <Route
            path="/project-hub/companies/:companyId/tasks"
            handle={PHCompanyDetails.createHandle(queryClient)}
            loader={withAuthControl(PHCompanyDetails.createLoader(queryClient))}
            element={<PHCompanyDetails.Component tabId="tasks" />}
          />
          <Route
            path="/project-hub/companies/:companyId/performance"
            handle={PHCompanyDetails.createHandle(queryClient)}
            loader={withAuthControl(PHCompanyDetails.createLoader(queryClient))}
            element={<PHCompanyDetails.Component tabId="performance" />}
          />
          <Route
            path="/project-hub/companies/:companyId/tasks/:taskId"
            handle={PHCompanyTask.createHandle(queryClient)}
            loader={withAuthControl(PHCompanyTask.createLoader(queryClient))}
            element={<PHCompanyTask.Component />}
          />
          {/* Legacy company-prefixed site routes - redirect to canonical Project Hub routes */}
          <Route
            path="/project-hub/companies/:companyId/sites/:siteId"
            element={<DeprecatedRouteRedirect targetTab="overview" />}
          />
          <Route
            path="/project-hub/companies/:companyId/sites/:siteId/overview"
            element={<DeprecatedRouteRedirect targetTab="overview" />}
          />
          <Route
            path="/project-hub/companies/:companyId/sites/:siteId/devices"
            element={<DeprecatedRouteRedirect targetTab="om" />}
          />
          <Route
            path="/project-hub/companies/:companyId/sites/:siteId/tasks"
            element={<DeprecatedRouteRedirect targetTab="tasks" />}
          />
          <Route path="/project-hub/companies/:companyId/sites/:siteId/telemetry" element={<TelemetryRedirect />} />
          <Route
            path="/project-hub/companies/:companyId/sites/:siteId/devices/add"
            handle={PHAddDevice.createHandle(queryClient)}
            loader={withAuthControl(PHAddDevice.createLoader(queryClient))}
            element={<PHAddDevice.Component />}
          />
          <Route
            path="/project-hub/companies/:companyId/sites/:siteId/devices/:deviceId"
            handle={PHDeviceDetails.createHandle()}
            loader={withAuthControl(PHDeviceDetails.createLoader(queryClient))}
            element={<PHDeviceDetails.Component />}
          />
          <Route
            path="/project-hub/companies/:companyId/sites/:siteId/devices/:deviceId/overview"
            handle={PHDeviceDetails.createHandle()}
            loader={withAuthControl(PHDeviceDetails.createLoader(queryClient))}
            element={<PHDeviceDetails.Component />}
          />
          <Route
            path="/project-hub/companies/:companyId/sites/:siteId/devices/:deviceId/tasks"
            handle={PHDeviceDetails.createHandle()}
            loader={withAuthControl(PHDeviceDetails.createLoader(queryClient))}
            element={<PHDeviceDetails.Component tabId="tasks" />}
          />
          <Route
            path="/project-hub/companies/:companyId/sites/:siteId/devices/:deviceId/alerts"
            handle={PHDeviceDetails.createHandle()}
            loader={withAuthControl(PHDeviceDetails.createLoader(queryClient))}
            element={<PHDeviceDetails.Component tabId="alerts" />}
          />
          <Route
            path="/project-hub/companies/:companyId/sites/:siteId/tasks/:taskId"
            element={<DeprecatedRouteRedirect targetTab="tasks" />}
          />
          {/* Simplified project routes without company prefix */}
          <Route
            path="/project-hub/projects/:siteId"
            handle={PHSiteDetails.createHandle(queryClient)}
            loader={withAuthControl(PHSiteDetails.createLoader(queryClient))}
            element={<PHSiteDetails.Component />}
          />
          <Route
            path="/project-hub/projects/:siteId/overview"
            handle={PHSiteDetails.createHandle(queryClient)}
            loader={withAuthControl(PHSiteDetails.createLoader(queryClient))}
            element={<PHSiteDetails.Component tabId="overview" />}
          />
          <Route
            path="/project-hub/projects/:siteId/om"
            handle={PHSiteDetails.createHandle(queryClient)}
            loader={withAuthControl(PHSiteDetails.createLoader(queryClient))}
            element={<PHSiteDetails.Component tabId="om" />}
          />
          <Route
            path="/project-hub/projects/:siteId/tasks"
            handle={PHSiteDetails.createHandle(queryClient)}
            loader={withAuthControl(PHSiteDetails.createLoader(queryClient))}
            element={<PHSiteDetails.Component tabId="tasks" />}
          />
          <Route
            path="/project-hub/projects/:siteId/finance"
            handle={PHSiteDetails.createHandle(queryClient)}
            loader={withAuthControl(PHSiteDetails.createLoader(queryClient))}
            element={<PHSiteDetails.Component tabId="finance" />}
          />
          <Route
            path="/project-hub/projects/:siteId/data-room"
            handle={PHSiteDetails.createHandle(queryClient)}
            loader={withAuthControl(PHSiteDetails.createLoader(queryClient))}
            element={<PHSiteDetails.Component tabId="data-room" />}
          />
          <Route
            path="/project-hub/projects/:siteId/reporting"
            handle={PHSiteDetails.createHandle(queryClient)}
            loader={withAuthControl(PHSiteDetails.createLoader(queryClient))}
            element={<PHSiteDetails.Component tabId="reporting" />}
          />
          <Route
            path="/project-hub/projects/:siteId/reconciliation"
            handle={PHSiteDetails.createHandle(queryClient)}
            loader={withAuthControl(PHSiteDetails.createLoader(queryClient))}
            element={<PHSiteDetails.Component tabId="reconciliation" />}
          />
        </Route>
        <Route path="/settings">
          <Route
            index
            element={<ProtectedSettingsRoute element={<SettingsPage.Component />} permission={[AdminType.system]} />}
            handle={SettingsPage.createHandle()}
          />
          <Route
            path="audit-logs"
            element={
              <ProtectedSettingsRoute
                element={<SettingsPage.Component tabId="audit-logs" />}
                permission={[AdminType.system]}
              />
            }
            handle={SettingsPage.createHandle()}
          />
          <Route
            path="health-checks"
            element={<ProtectedSettingsRoute element={<HealthChecksPage />} permission={[AdminType.system]} />}
          />
          <Route path="access-health" element={<Navigate to="/settings/health-checks" replace />} />
        </Route>
        <Route path="*" element={<Navigate to="/" />} />
      </Route>
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<Login />} />
        <Route path="/forgot-password" element={<PasswordResetRequest />} />
        <Route path="/reset-notification" element={<PasswordResetNotification />} />
        <Route path="/password-reset" element={<PasswordReset />} />
        <Route path="/password-reset-success" element={<PasswordResetSuccess />} />
        <Route path="/password-reset-invalid" element={<PasswordResetInvalid />} />
        <Route path="/sign-up" element={<SignUp />} />
        <Route path="*" element={<Navigate to="/login" />} />
      </Route>
    </Route>
  )
);

function App() {
  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
      <ThemeModeProvider>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <NotificationsProvider>
              <ActionProcessorsProvider>
                <RouterProvider router={router} />
              </ActionProcessorsProvider>
            </NotificationsProvider>
          </AuthProvider>
        </QueryClientProvider>
      </ThemeModeProvider>
    </LocalizationProvider>
  );
}

export default App;

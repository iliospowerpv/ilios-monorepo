import React from 'react';
import { Route, createBrowserRouter, createRoutesFromElements, Navigate } from 'react-router-dom';
// Providers
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { ThemeProvider } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from 'react-router-dom';
import { BaseLayout } from './components/layout/BaseLayout/BaseLayout';
import { AuthLayout } from './components/layout/AuthLayout/AuthLayout';
import theme from './utils/styles/theme';
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

import {
  SiteTask as AMSiteTask,
  CompanyTask as AMCompanyTask,
  Root as AMRoot,
  CompanyDetails as AMCompanyDetails,
  SiteDetails as AMSiteDetails,
  DeviceDetails as AMDeviceDetails,
  AddDevice as AMAddDevice,
  ModuleContainer as AMModuleContainer
} from './modules/asset-management';
import {
  AllCompanies as OMAllCompanies,
  CompanyDetails as OMCompanyDetails,
  SiteDetails as OMSiteDetails,
  // DeviceDetails as OMDeviceDetails,
  createCompanyDetailsHandle,
  createCompanyDetailsLoader,
  createSiteDetailsHandle,
  createSiteCrumbsLoader,
  // createDeviceDetailsHandle,
  // createDeviceDetailsLoader,
  CompanyTask as OMCompanyTask,
  ModuleContainer as OMModuleContainer
} from './modules/operations-and-maintenance';
import {
  SettingsPage,
  SettingsAddUser,
  SettingsEditUser,
  SettingsAddCompany,
  SettingsEditCompany,
  SettingsAddSite,
  SettingsEditSite,
  SettingsMyCompanyPage,
  SettingsEditMyCompany,
  SettingsMyCompanyEditSite,
  SettingsEditMyCompanyUser,
  SettingsAddMyCompanyUser,
  SettingsManageConnections,
  SettingsAddMyCompanySite
} from './modules/settings';
import { SiteTask as OMSiteTask } from './modules/security';
import { DashboardPage, ModuleContainer as DashboardModuleContainer } from './modules/dashboard';
import {
  DueDiligencePage as DPDiligencePage,
  SitesPage as DPSitesPage,
  SitePage as DPSitePage,
  DueDiligenceDocument as DPDueDiligenceDocument,
  ModuleContainer as DDModuleContainer
} from './modules/due-diligence';
import { ErrorLayout } from './components/layout/ErrorLayout/ErrorLayout';
import { PortfolioPage, ModuleContainer as PortfolioModuleContainer } from './modules/my-portfolio';
import { AllReports, ModuleContainer as ReportsModuleContainer } from './modules/reports';

// initialization
const queryClient = new QueryClient();

const AdminType = {
  system: 'is_system_user',
  full: 'company_admin_full',
  view: 'company_view'
};

type ProtectedRouteProps = {
  element: React.ReactElement;
  permission: string[];
  path?: string;
};

const ProtectedSettingsRoute = ({ element, permission, path }: ProtectedRouteProps) => {
  const { isAuthenticated, user } = useAuth();

  if (isAuthenticated) {
    const isSystem = permission.some(perm => perm === 'is_system_user');
    const isCompanyAdmin = permission.some(perm => perm === 'company_admin_full');
    if (isSystem && user?.is_system_user) {
      return element;
    } else if (path === '/settings' && user?.role?.permissions?.['Settings Page']?.view) {
      return <Navigate to="/settings/my-company" replace />;
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
        <Route path="/dashboard" element={<DashboardModuleContainer />}>
          <Route index handle={DashboardPage.createHandle()} element={<DashboardPage.Component />} />
        </Route>
        <Route path="/my-portfolio" element={<PortfolioModuleContainer />}>
          <Route index handle={PortfolioPage.createHandle()} element={<PortfolioPage.Component />} />
        </Route>
        <Route path="/reports" element={<ReportsModuleContainer />}>
          <Route index handle={AllReports.createHandle()} element={<AllReports.Component />} />
        </Route>
        <Route path="/due-diligence" element={<DDModuleContainer />}>
          <Route index handle={DPDiligencePage.createHandle()} element={<DPDiligencePage.Component />} />
          <Route
            path="/due-diligence/companies/:companyId/sites"
            handle={DPSitesPage.createHandle(queryClient)}
            loader={DPSitesPage.createLoader(queryClient)}
            element={<DPSitesPage.Component />}
          />
          <Route
            path="/due-diligence/companies/:companyId/sites/:siteId"
            handle={DPSitePage.createHandle()}
            loader={DPSitePage.createLoader(queryClient)}
            element={<DPSitePage.Component />}
          />
          <Route
            path="/due-diligence/companies/:companyId/sites/:siteId/overview"
            handle={DPSitePage.createHandle()}
            loader={DPSitePage.createLoader(queryClient)}
            element={<DPSitePage.Component tabId="overview" />}
          />
          <Route
            path="/due-diligence/companies/:companyId/sites/:siteId/due-diligence"
            handle={DPSitePage.createHandle()}
            loader={DPSitePage.createLoader(queryClient)}
            element={<DPSitePage.Component tabId="diligence" />}
          />
          <Route
            path="/due-diligence/companies/:companyId/sites/:siteId/due-diligence/:documentId"
            handle={DPDueDiligenceDocument.createHandle(queryClient)}
            loader={withAuthControl(DPDueDiligenceDocument.createLoader(queryClient))}
            element={<DPDueDiligenceDocument.Component />}
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
          <Route
            path="companies/:companyId/sites/:siteId"
            handle={createSiteDetailsHandle()}
            loader={withAuthControl(createSiteCrumbsLoader(queryClient))}
            element={<OMSiteDetails />}
          />
          <Route
            path="companies/:companyId/sites/:siteId/overview"
            handle={createSiteDetailsHandle()}
            loader={withAuthControl(createSiteCrumbsLoader(queryClient))}
            element={<OMSiteDetails tabId="overview" />}
          />
          <Route
            path="companies/:companyId/sites/:siteId/devices"
            handle={createSiteDetailsHandle()}
            loader={withAuthControl(createSiteCrumbsLoader(queryClient))}
            element={<OMSiteDetails tabId="devices" />}
          />
          <Route
            path="companies/:companyId/sites/:siteId/alerts"
            handle={createSiteDetailsHandle()}
            loader={withAuthControl(createSiteCrumbsLoader(queryClient))}
            element={<OMSiteDetails tabId="alerts" />}
          />
          <Route
            path="companies/:companyId/sites/:siteId/security"
            handle={createSiteDetailsHandle()}
            loader={withAuthControl(createSiteCrumbsLoader(queryClient))}
            element={<OMSiteDetails tabId="security" />}
          />
          <Route
            path="companies/:companyId/sites/:siteId/tasks"
            handle={createSiteDetailsHandle()}
            loader={withAuthControl(createSiteCrumbsLoader(queryClient))}
            element={<OMSiteDetails tabId="tasks" />}
          />
          <Route
            path="companies/:companyId/sites/:siteId/tasks/:taskId"
            handle={OMSiteTask.createHandle(queryClient)}
            loader={withAuthControl(OMSiteTask.createLoader(queryClient))}
            element={<OMSiteTask.Component />}
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
        <Route path="/asset-management" element={<AMModuleContainer />}>
          <Route path="/asset-management" handle={AMRoot.createHandle()} element={<AMRoot.Component />} />
          <Route
            path="/asset-management/overview"
            handle={AMRoot.createHandle()}
            element={<AMRoot.Component tabId="overview" />}
          />
          <Route
            path="/asset-management/sites"
            handle={AMRoot.createHandle()}
            element={<AMRoot.Component tabId="sites" />}
          />
          <Route
            path="/asset-management/companies/:companyId"
            handle={AMCompanyDetails.createHandle(queryClient)}
            loader={withAuthControl(AMCompanyDetails.createLoader(queryClient))}
            element={<AMCompanyDetails.Component />}
          />
          <Route
            path="/asset-management/companies/:companyId/overview"
            handle={AMCompanyDetails.createHandle(queryClient)}
            loader={withAuthControl(AMCompanyDetails.createLoader(queryClient))}
            element={<AMCompanyDetails.Component tabId="overview" />}
          />
          <Route
            path="/asset-management/companies/:companyId/sites"
            handle={AMCompanyDetails.createHandle(queryClient)}
            loader={withAuthControl(AMCompanyDetails.createLoader(queryClient))}
            element={<AMCompanyDetails.Component tabId="sites" />}
          />
          <Route
            path="/asset-management/companies/:companyId/tasks"
            handle={AMCompanyDetails.createHandle(queryClient)}
            loader={withAuthControl(AMCompanyDetails.createLoader(queryClient))}
            element={<AMCompanyDetails.Component tabId="tasks" />}
          />
          <Route
            path="/asset-management/companies/:companyId/tasks/:taskId"
            handle={AMCompanyTask.createHandle(queryClient)}
            loader={withAuthControl(AMCompanyTask.createLoader(queryClient))}
            element={<AMCompanyTask.Component />}
          />
          <Route
            path="/asset-management/companies/:companyId/sites/:siteId"
            handle={AMSiteDetails.createHandle(queryClient)}
            loader={withAuthControl(AMSiteDetails.createLoader(queryClient))}
            element={<AMSiteDetails.Component />}
          />
          <Route
            path="/asset-management/companies/:companyId/sites/:siteId/overview"
            handle={AMSiteDetails.createHandle(queryClient)}
            loader={withAuthControl(AMSiteDetails.createLoader(queryClient))}
            element={<AMSiteDetails.Component tabId="overview" />}
          />
          <Route
            path="/asset-management/companies/:companyId/sites/:siteId/devices"
            handle={AMSiteDetails.createHandle(queryClient)}
            loader={withAuthControl(AMSiteDetails.createLoader(queryClient))}
            element={<AMSiteDetails.Component tabId="devices" />}
          />
          <Route
            path="/asset-management/companies/:companyId/sites/:siteId/tasks"
            handle={AMSiteDetails.createHandle(queryClient)}
            loader={withAuthControl(AMSiteDetails.createLoader(queryClient))}
            element={<AMSiteDetails.Component tabId="tasks" />}
          />
          <Route
            path="/asset-management/companies/:companyId/sites/:siteId/devices/add"
            loader={withAuthControl(AMAddDevice.createLoader(queryClient))}
            handle={AMAddDevice.createHandle(queryClient)}
            element={<AMAddDevice.Component />}
          />
          <Route
            path="/asset-management/companies/:companyId/sites/:siteId/devices/:deviceId"
            loader={withAuthControl(AMDeviceDetails.createLoader(queryClient))}
            handle={AMDeviceDetails.createHandle()}
            element={<AMDeviceDetails.Component />}
          />
          <Route
            path="/asset-management/companies/:companyId/sites/:siteId/devices/:deviceId/overview"
            handle={AMDeviceDetails.createHandle()}
            loader={withAuthControl(AMDeviceDetails.createLoader(queryClient))}
            element={<AMDeviceDetails.Component tabId="overview" />}
          />
          <Route
            path="/asset-management/companies/:companyId/sites/:siteId/devices/:deviceId/tasks"
            handle={AMDeviceDetails.createHandle()}
            loader={withAuthControl(AMDeviceDetails.createLoader(queryClient))}
            element={<AMDeviceDetails.Component tabId="tasks" />}
          />
          <Route
            path="/asset-management/companies/:companyId/sites/:siteId/tasks/:taskId"
            handle={AMSiteTask.createHandle(queryClient)}
            loader={withAuthControl(AMSiteTask.createLoader(queryClient))}
            element={<AMSiteTask.Component />}
          />
        </Route>
        <Route path="/settings">
          <Route
            index
            element={
              <ProtectedSettingsRoute
                element={<SettingsPage.Component />}
                permission={[AdminType.system]}
                path="/settings"
              />
            }
            handle={SettingsPage.createHandle()}
          />
          <Route
            path="users"
            element={
              <ProtectedSettingsRoute
                element={<SettingsPage.Component tabId="users" />}
                permission={[AdminType.system]}
              />
            }
            handle={SettingsPage.createHandle()}
          />
          <Route
            path="companies"
            element={
              <ProtectedSettingsRoute
                element={<SettingsPage.Component tabId="companies" />}
                permission={[AdminType.system]}
              />
            }
            handle={SettingsPage.createHandle()}
          />
          <Route
            path="sites"
            element={
              <ProtectedSettingsRoute
                element={<SettingsPage.Component tabId="sites" />}
                permission={[AdminType.system]}
              />
            }
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
            path="users/add"
            handle={SettingsAddUser.createHandle()}
            element={<ProtectedSettingsRoute element={<SettingsAddUser.Component />} permission={[AdminType.system]} />}
          />
          <Route
            path="users/:id/edit"
            handle={SettingsEditUser.createHandle()}
            element={
              <ProtectedSettingsRoute element={<SettingsEditUser.Component />} permission={[AdminType.system]} />
            }
          />
          <Route
            path="company/add"
            handle={SettingsAddCompany.createHandle()}
            element={
              <ProtectedSettingsRoute element={<SettingsAddCompany.Component />} permission={[AdminType.system]} />
            }
          />
          <Route
            path="company/:companyId"
            handle={SettingsEditCompany.createHandle()}
            element={
              <ProtectedSettingsRoute
                element={<SettingsEditCompany.Component />}
                permission={[AdminType.system, AdminType.full]}
              />
            }
          />
          <Route
            path="company/:companyId/site/add"
            handle={SettingsAddSite.createHandle()}
            element={
              <ProtectedSettingsRoute
                element={<SettingsAddSite.Component />}
                permission={[AdminType.system, AdminType.full]}
              />
            }
          />
          <Route
            path="company/:companyId/site/:siteId/edit"
            handle={SettingsEditSite.createHandle()}
            element={
              <ProtectedSettingsRoute
                element={<SettingsEditSite.Component />}
                permission={[AdminType.system, AdminType.full]}
              />
            }
          />
          <Route
            path="my-company"
            handle={SettingsMyCompanyPage.createHandle()}
            element={
              <ProtectedSettingsRoute element={<SettingsMyCompanyPage.Component />} permission={[AdminType.full]} />
            }
          />
          <Route
            path="my-company/edit"
            handle={SettingsEditMyCompany.createHandle()}
            element={
              <ProtectedSettingsRoute element={<SettingsEditMyCompany.Component />} permission={[AdminType.full]} />
            }
          />
          <Route
            path="my-company/overview"
            handle={SettingsMyCompanyPage.createHandle()}
            element={
              <ProtectedSettingsRoute
                element={<SettingsMyCompanyPage.Component tabId="overview" />}
                permission={[AdminType.full, AdminType.view]}
              />
            }
          />
          <Route
            path="my-company/sites"
            handle={SettingsMyCompanyPage.createHandle()}
            element={
              <ProtectedSettingsRoute
                element={<SettingsMyCompanyPage.Component tabId="sites" />}
                permission={[AdminType.full, AdminType.view]}
              />
            }
          />
          <Route
            path="my-company/sites/add"
            handle={SettingsAddMyCompanySite.createHandle()}
            element={
              <ProtectedSettingsRoute
                element={<SettingsAddMyCompanySite.Component />}
                permission={[AdminType.full, AdminType.view]}
              />
            }
          />
          <Route
            path="my-company/site/:siteId/edit"
            handle={SettingsMyCompanyEditSite.createHandle()}
            element={
              <ProtectedSettingsRoute
                element={<SettingsMyCompanyEditSite.Component />}
                permission={[AdminType.full, AdminType.view]}
              />
            }
          />
          <Route
            path="my-company/users"
            handle={SettingsMyCompanyPage.createHandle()}
            element={
              <ProtectedSettingsRoute
                element={<SettingsMyCompanyPage.Component tabId="users" />}
                permission={[AdminType.full, AdminType.view]}
              />
            }
          />
          <Route
            path="my-company/users/:userId/edit"
            handle={SettingsEditMyCompanyUser.createHandle()}
            element={
              <ProtectedSettingsRoute
                element={<SettingsEditMyCompanyUser.Component />}
                permission={[AdminType.full, AdminType.view]}
              />
            }
          />
          <Route
            path="my-company/users/add"
            handle={SettingsAddMyCompanyUser.createHandle()}
            element={
              <ProtectedSettingsRoute
                element={<SettingsAddMyCompanyUser.Component />}
                permission={[AdminType.full, AdminType.view]}
              />
            }
          />
          <Route
            path="company/:companyId/connections"
            handle={SettingsManageConnections.createHandle()}
            element={
              <ProtectedSettingsRoute
                element={<SettingsManageConnections.Component />}
                permission={[AdminType.system, AdminType.full]}
              />
            }
          />
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
      <ThemeProvider theme={theme}>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <NotificationsProvider>
              <ActionProcessorsProvider>
                <RouterProvider router={router} />
              </ActionProcessorsProvider>
            </NotificationsProvider>
          </AuthProvider>
        </QueryClientProvider>
      </ThemeProvider>
    </LocalizationProvider>
  );
}

export default App;

import React, { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate, useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Button from '@mui/material/Button';
import SpaceDashboardIcon from '@mui/icons-material/SpaceDashboard';
import FolderIcon from '@mui/icons-material/Folder';
import WhatshotIcon from '@mui/icons-material/Whatshot';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import AssignmentTurnedInIcon from '@mui/icons-material/AssignmentTurnedIn';
import AssessmentIcon from '@mui/icons-material/Assessment';
import FactCheckOutlinedIcon from '@mui/icons-material/FactCheckOutlined';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import ArchiveIcon from '@mui/icons-material/Archive';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import { siteDetailsQuery } from './loader';
import Overview from './tabs/Overview/Overview';
import DataRoom from './tabs/DataRoom/DataRoom';
import OM from './tabs/OM/OM';
import Finance from './tabs/Finance/Finance';
import Tasks from './tabs/Tasks/Tasks';
import Reporting from './tabs/Reporting/Reporting';
import Reconciliation from './tabs/Reconciliation/Reconciliation';
import type { AssetManagementSiteDetailsTabProps } from './tabs/types';
import { useEntityContext } from '../../../../contexts/entityContext';
import { useAccess } from '../../../../hooks/access/access';
import { useAuth } from '../../../../contexts/auth/auth';
import { ApiClient } from '../../../../api';
import ArchiveConfirmationModal from '../../../../components/common/ArchiveConfirmationModal/ArchiveConfirmationModal';

interface TabData {
  id: string;
  label: string;
  link: string;
  disabled?: boolean;
  icon: React.ReactElement;
  content: React.FC<AssetManagementSiteDetailsTabProps> | null;
}

type TabType = 'overview' | 'data-room' | 'om' | 'finance' | 'tasks' | 'reporting' | 'reconciliation';

interface AssetManagementSiteDetailsProps {
  tabId?: TabType;
}

const baseTabs: TabData[] = [
  {
    id: 'overview',
    label: 'Overview',
    link: '/project-hub/projects/:siteId/overview',
    disabled: false,
    icon: <SpaceDashboardIcon />,
    content: Overview
  },
  {
    id: 'data-room',
    label: 'Data Room',
    link: '/project-hub/projects/:siteId/data-room',
    disabled: false,
    icon: <FolderIcon />,
    content: DataRoom
  },
  {
    id: 'om',
    label: 'O&M',
    link: '/project-hub/projects/:siteId/om',
    disabled: false,
    icon: <WhatshotIcon />,
    content: OM
  },
  {
    id: 'finance',
    label: 'Finance',
    link: '/project-hub/projects/:siteId/finance',
    disabled: false,
    icon: <AccountBalanceWalletIcon />,
    content: Finance
  },
  {
    id: 'tasks',
    label: 'Tasks',
    link: '/project-hub/projects/:siteId/tasks',
    disabled: false,
    icon: <AssignmentTurnedInIcon />,
    content: Tasks
  },
  {
    id: 'reporting',
    label: 'Reporting',
    link: '/project-hub/projects/:siteId/reporting',
    disabled: false,
    icon: <AssessmentIcon />,
    content: Reporting
  }
];

// Admin-only, read-only assumptions reconciliation. Visibility mirrors the
// backend gate (system user OR Diligence:view); the endpoint enforces auth.
const reconciliationTab: TabData = {
  id: 'reconciliation',
  label: 'Reconciliation',
  link: '/project-hub/projects/:siteId/reconciliation',
  disabled: false,
  icon: <FactCheckOutlinedIcon />,
  content: Reconciliation
};

const legacyTabAliases: Record<string, TabType> = {
  devices: 'om',
  telemetry: 'om',
  diligence: 'data-room'
};

export const AssetManagementSiteDetails: React.FC<AssetManagementSiteDetailsProps> = ({ tabId }) => {
  const { siteId } = useParams();
  const isValidId = !!siteId && Number.isSafeInteger(Number.parseInt(siteId));
  const { setCurrentCompany, setCurrentProject } = useEntityContext();
  const { isSystemUser } = useAccess();
  const { user } = useAuth();
  const canViewReconciliation = !!user?.is_system_user || !!user?.role?.permissions?.['Diligence']?.view;
  const tabsData = useMemo<TabData[]>(
    () => (canViewReconciliation ? [...baseTabs, reconciliationTab] : baseTabs),
    [canViewReconciliation]
  );
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [archiveModalOpen, setArchiveModalOpen] = useState(false);
  const [toast, setToast] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success'
  });

  const resolvedTab = tabId ? legacyTabAliases[tabId] || tabId : 'overview';
  const activeTab = resolvedTab as TabType;

  const { data: siteDetails, isLoading: isLoadingSiteDetails } = useQuery(
    siteDetailsQuery(isValidId ? Number.parseInt(siteId) : -1, isValidId, true)
  );

  const archiveMutation = useMutation({
    mutationFn: () => ApiClient.assetManagement.archiveSite(Number.parseInt(siteId as string)),
    onSuccess: data => {
      setArchiveModalOpen(false);
      setToast({ open: true, message: data.message, severity: 'success' });
      queryClient.invalidateQueries({ queryKey: ['site'] });
      queryClient.invalidateQueries({ queryKey: ['company'] });
      queryClient.invalidateQueries({ queryKey: ['workspace'] });
      queryClient.invalidateQueries({ queryKey: ['home-workspace'] });
      queryClient.invalidateQueries({ queryKey: ['accessible-entities'] });
      queryClient.invalidateQueries({ queryKey: ['accessible-entities-picker'] });
      setTimeout(() => {
        if (siteDetails?.company?.id) {
          navigate(`/project-hub/companies/${siteDetails.company.id}/sites`);
        } else {
          navigate('/project-hub/companies');
        }
      }, 1500);
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail || 'Failed to archive project';
      setToast({ open: true, message: detail, severity: 'error' });
    }
  });

  useEffect(() => {
    if (siteDetails) {
      setCurrentCompany({ id: siteDetails.company.id, name: siteDetails.company.name });
      setCurrentProject({ id: siteDetails.id, name: siteDetails.name });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteDetails?.id, siteDetails?.company?.id]);

  // A non-permitted user reaching /reconciliation directly must see an explicit
  // unauthorized state rather than silently falling back to Overview.
  const showReconciliationUnauthorized = activeTab === 'reconciliation' && !canViewReconciliation;

  const DisplayContent = React.useMemo(() => {
    const tab = tabsData.find(({ id }) => id === activeTab);
    return tab ? tab.content : baseTabs[0].content;
  }, [activeTab, tabsData]);

  if (!DisplayContent || isLoadingSiteDetails || !siteDetails) return null;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: '24px' }}>
        <Typography variant="h4" sx={{ fontWeight: 600 }} fontSize="34px" lineHeight="42px">
          {siteDetails.name}
        </Typography>
        {isSystemUser && (
          <Button
            variant="outlined"
            color="warning"
            startIcon={<ArchiveIcon />}
            onClick={() => setArchiveModalOpen(true)}
          >
            Archive
          </Button>
        )}
      </Box>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabsData.some(tab => tab.id === activeTab) ? activeTab : false}>
          {tabsData.map(tab => (
            <Tab
              key={tab.id}
              label={tab.label}
              component={Link}
              to={tab.link.replace(':siteId', String(siteId))}
              value={tab.id}
              disabled={tab.disabled}
              icon={tab.icon}
            />
          ))}
        </Tabs>
      </Box>
      <div role="tabpanel">
        <Box sx={{ paddingTop: '24px' }}>
          {showReconciliationUnauthorized ? (
            <Alert severity="warning" icon={<LockOutlinedIcon />} data-testid="reconciliation-tab-unauthorized">
              <AlertTitle>Access restricted</AlertTitle>
              You don&apos;t have permission to view the assumptions reconciliation for this project. This view requires
              Diligence access.
            </Alert>
          ) : (
            <DisplayContent siteDetails={siteDetails} />
          )}
        </Box>
      </div>

      <ArchiveConfirmationModal
        open={archiveModalOpen}
        onClose={() => setArchiveModalOpen(false)}
        onConfirm={() => archiveMutation.mutate()}
        entityType="project"
        entityName={siteDetails.name}
        isLoading={archiveMutation.isPending}
      />

      <Snackbar
        open={toast.open}
        autoHideDuration={4000}
        onClose={() => setToast(prev => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={toast.severity} onClose={() => setToast(prev => ({ ...prev, open: false }))}>
          {toast.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default AssetManagementSiteDetails;

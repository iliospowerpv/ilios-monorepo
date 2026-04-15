import React, { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate, useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Button from '@mui/material/Button';
import SpaceDashboardIcon from '@mui/icons-material/SpaceDashboard';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import AssignmentTurnedInIcon from '@mui/icons-material/AssignmentTurnedIn';
import ArchiveIcon from '@mui/icons-material/Archive';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';
import { companyDetailsQuery } from './loader';
import Overview from './tabs/Overview/Overview';
import Sites from './tabs/Sites/Sites';
import Tasks from './tabs/Tasks/Tasks';
import type { AssetManagementCompanyDetailsTabProps } from './tabs/types';
import { useEntityContext } from '../../../../contexts/entityContext';
import { useAccess } from '../../../../hooks/access/access';
import { ApiClient } from '../../../../api';
import ArchiveConfirmationModal from '../../../../components/common/ArchiveConfirmationModal/ArchiveConfirmationModal';

interface TabData {
  id: string;
  label: string;
  link: string;
  disabled?: boolean;
  icon: React.ReactElement;
  content: React.FC<AssetManagementCompanyDetailsTabProps> | null;
}

type TabType = 'overview' | 'sites' | 'tasks';

interface AssetManagementCompanyDetailsProps {
  tabId?: TabType;
}

const tabsData: TabData[] = [
  {
    id: 'overview',
    label: 'Overview',
    link: '/project-hub/companies/:companyId/overview',
    disabled: false,
    icon: <SpaceDashboardIcon />,
    content: Overview
  },
  {
    id: 'sites',
    label: 'Projects',
    link: '/project-hub/companies/:companyId/sites',
    disabled: false,
    icon: <LocationOnIcon />,
    content: Sites
  },
  {
    id: 'tasks',
    label: 'Tasks',
    link: '/project-hub/companies/:companyId/tasks',
    disabled: false,
    icon: <AssignmentTurnedInIcon />,
    content: Tasks
  }
];

export const AssetManagementCompanyDetails: React.FC<AssetManagementCompanyDetailsProps> = ({ tabId }) => {
  const { companyId } = useParams();
  const isValidId = !!companyId && Number.isSafeInteger(Number.parseInt(companyId));
  const activeTab = tabId || 'overview';
  const { setCurrentCompany, setCurrentProject } = useEntityContext();
  const { isSystemUser } = useAccess();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [archiveModalOpen, setArchiveModalOpen] = useState(false);
  const [toast, setToast] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success'
  });

  const {
    data: companyDetails,
    isLoading: isLoadingCompanyDetails,
    error: companyDetailsLoadingError
  } = useQuery(companyDetailsQuery(isValidId ? Number.parseInt(companyId) : -1, isValidId));

  const archiveMutation = useMutation({
    mutationFn: () => ApiClient.assetManagement.archiveCompany(Number.parseInt(companyId as string)),
    onSuccess: data => {
      setArchiveModalOpen(false);
      setToast({ open: true, message: data.message, severity: 'success' });
      queryClient.invalidateQueries({ queryKey: ['company'] });
      queryClient.invalidateQueries({ queryKey: ['workspace'] });
      queryClient.invalidateQueries({ queryKey: ['home-workspace'] });
      queryClient.invalidateQueries({ queryKey: ['accessible-entities'] });
      queryClient.invalidateQueries({ queryKey: ['accessible-entities-picker'] });
      setTimeout(() => navigate('/project-hub'), 1500);
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail || 'Failed to archive company';
      setToast({ open: true, message: detail, severity: 'error' });
    }
  });

  useEffect(() => {
    if (companyDetails) {
      setCurrentCompany({ id: companyDetails.id, name: companyDetails.name });
      setCurrentProject(null);
    }
  }, [companyDetails, setCurrentCompany, setCurrentProject]);

  React.useEffect(() => {
    if (companyDetailsLoadingError) {
      throw companyDetailsLoadingError;
    }
  }, [companyDetailsLoadingError]);

  const DisplayContent = React.useMemo(() => {
    const tab = tabsData.find(({ id }) => id === activeTab);
    return tab ? tab.content : null;
  }, [activeTab]);

  if (!DisplayContent || isLoadingCompanyDetails || !companyDetails) return null;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: '24px' }}>
        <Typography variant="h4" sx={{ fontWeight: 600 }} fontSize="34px" lineHeight="42px">
          {companyDetails.name}
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
        <Tabs value={activeTab}>
          {tabsData.map(tab => (
            <Tab
              key={tab.id}
              label={tab.label}
              component={Link}
              to={tab.link.replace(':companyId', companyId as string)}
              value={tab.id}
              disabled={tab.disabled}
              icon={tab.icon}
            />
          ))}
        </Tabs>
      </Box>
      <div role="tabpanel">
        <Box sx={{ paddingTop: '24px' }}>
          <DisplayContent companyDetails={companyDetails} />
        </Box>
      </div>

      <ArchiveConfirmationModal
        open={archiveModalOpen}
        onClose={() => setArchiveModalOpen(false)}
        onConfirm={() => archiveMutation.mutate()}
        entityType="company"
        entityName={companyDetails.name}
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

export default AssetManagementCompanyDetails;

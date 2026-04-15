import React, { useState, useCallback, useMemo } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableRow from '@mui/material/TableRow';
import Grid from '@mui/material/Grid';
import Paper from '@mui/material/Paper';
import Button from '@mui/material/Button';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import WhatshotIcon from '@mui/icons-material/Whatshot';
import FactCheckIcon from '@mui/icons-material/FactCheck';
import { AssetManagementCompanyDetailsTabProps } from '../types';
import formatFloatValue from '../../../../../..//utils/formatters/formatFloatValue';
import formatPhoneNumber from '../../../../../../utils/formatters/formatPhoneNumber';
import { useEntityContext } from '../../../../../../contexts/entityContext';
import { ProjectPicker, useProjectNavigation, type ProjectHubTab } from '../../../../../../components/common/ProjectPicker';
import { useAccessibleEntities } from '../../../../../../hooks/useAccessibleEntities';

interface InfoBoxProps {
  title: string;
  infoTableData: { field: string; value: string | number | null }[];
}

const InfoBox: React.FC<InfoBoxProps> = ({ title, infoTableData }) => (
  <Box
    display="flex"
    flexDirection="column"
    flexGrow={1}
    padding="16px"
    sx={{ border: theme => `1px solid ${theme.palette.divider}` }}
  >
    <Typography variant="h6" mb="6px">
      {title}
    </Typography>
    <Table sx={{ width: '100%' }} size="small">
      <TableBody>
        {infoTableData.map(({ field, value }) => (
          <TableRow key={field} sx={{ '& .MuiTableCell-root': { px: 0, pb: 0, pt: 1, border: 'none' } }}>
            <TableCell component="th" scope="row" sx={{ fontWeight: 600 }}>
              {`${field}:`}
            </TableCell>
            <TableCell align="right">{typeof value !== 'number' ? value || '-' : value}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </Box>
);

const moduleActions: { tab: ProjectHubTab; label: string; icon: React.ReactElement }[] = [
  { tab: 'overview', label: 'Asset Management', icon: <AccountBalanceIcon /> },
  { tab: 'finance', label: 'Finance', icon: <AccountBalanceWalletIcon /> },
  { tab: 'om', label: 'O&M', icon: <WhatshotIcon /> },
  { tab: 'data-room', label: 'Data Room', icon: <FactCheckIcon /> }
];

export const OverviewTab: React.FC<AssetManagementCompanyDetailsTabProps> = ({ companyDetails }) => {
  const { currentProject, setCurrentProject, setCurrentScope } = useEntityContext();
  const { navigateToProjectHub } = useProjectNavigation();
  const { getProjectsByCompanyId } = useAccessibleEntities();
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerTab, setPickerTab] = useState<ProjectHubTab | null>(null);

  const companyProjects = useMemo(
    () => getProjectsByCompanyId(companyDetails.id),
    [companyDetails.id, getProjectsByCompanyId]
  );

  const handleModuleAction = useCallback(
    (tab: ProjectHubTab) => {
      const lastProjectInCompany =
        currentProject && companyProjects.some(p => p.id === currentProject.id) ? currentProject : null;

      if (lastProjectInCompany) {
        navigateToProjectHub(lastProjectInCompany.id, tab);
      } else if (companyProjects.length === 1) {
        setCurrentProject({ id: companyProjects[0].id, name: companyProjects[0].name });
        setCurrentScope('project');
        navigateToProjectHub(companyProjects[0].id, tab);
      } else {
        setPickerTab(tab);
        setPickerOpen(true);
      }
    },
    [currentProject, companyProjects, navigateToProjectHub, setCurrentProject, setCurrentScope]
  );

  const handlePickerSelect = useCallback(
    (project: { id: number; name: string }) => {
      setCurrentProject({ id: project.id, name: project.name });
      setCurrentScope('project');
      navigateToProjectHub(project.id, pickerTab || 'overview');
      setPickerOpen(false);
      setPickerTab(null);
    },
    [setCurrentProject, setCurrentScope, navigateToProjectHub, pickerTab]
  );

  const companyInfo = {
    title: 'Company Information',
    infoTableData: [
      { field: 'Name', value: companyDetails.name },
      { field: 'Email', value: companyDetails.email },
      { field: 'Phone Number', value: formatPhoneNumber(companyDetails.phone) },
      { field: 'Address', value: companyDetails.address }
    ]
  };

  const sitesSummary = {
    title: 'Portfolio Summary',
    infoTableData: [
      { field: 'Total Projects', value: companyDetails.total_sites },
      { field: 'Projects Placed in Service', value: companyDetails.sites_placed_in_service },
      { field: 'Projects Under Construction', value: companyDetails.sites_under_construction },
      { field: 'Projects Sold', value: companyDetails.sites_sold },
      { field: 'Projects Decommissioned', value: companyDetails.sites_decommissioned },
      { field: 'System Size', value: formatFloatValue(companyDetails.total_capacity) }
    ]
  };

  const pickerTitle = pickerTab === 'data-room'
    ? 'Data Room'
    : pickerTab === 'finance'
      ? 'Finance'
      : pickerTab === 'om'
        ? 'O&M'
        : 'Asset Management';

  return (
    <Box paddingTop={1} sx={{ flexGrow: 1 }}>
      <Grid container spacing={2}>
        <Grid item xs={12} md={6} lg={4}>
          <InfoBox title={companyInfo.title} infoTableData={companyInfo.infoTableData} />
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <Box display="flex" flexGrow={1}>
            <InfoBox title={sitesSummary.title} infoTableData={sitesSummary.infoTableData} />
          </Box>
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Quick Actions
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {moduleActions.map(({ tab, label, icon }) => (
                <Button
                  key={tab}
                  variant="outlined"
                  startIcon={icon}
                  fullWidth
                  sx={{ justifyContent: 'flex-start' }}
                  onClick={() => handleModuleAction(tab)}
                >
                  {label}
                </Button>
              ))}
            </Box>
          </Paper>
        </Grid>
      </Grid>

      <ProjectPicker
        open={pickerOpen}
        onClose={() => {
          setPickerOpen(false);
          setPickerTab(null);
        }}
        onSelect={handlePickerSelect}
        title={`Select a Project for ${pickerTitle}`}
        companyId={companyDetails.id}
      />
    </Box>
  );
};

export default OverviewTab;

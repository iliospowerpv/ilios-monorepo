import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableRow from '@mui/material/TableRow';
import Grid from '@mui/material/Grid';
import ModeEditIcon from '@mui/icons-material/ModeEdit';
import LinkIcon from '@mui/icons-material/Link';
import Stack from '@mui/material/Stack';

import type { CompanyDetails } from '../../../../../../api';
import { useNavigate } from 'react-router-dom';
import formatFloatValue from '../../../../../../utils/formatters/formatFloatValue';
import formatPhoneNumber from '../../../../../../utils/formatters/formatPhoneNumber';

export interface CompanyDetailsTabProps {
  companyDetails: CompanyDetails;
}

interface InfoBoxProps {
  title: string;
  infoTableData: { field: string; value: string | number | null }[];
  id?: number;
}

const InfoBox: React.FC<InfoBoxProps> = ({ title, infoTableData, id }) => {
  const navigate = useNavigate();

  return (
    <Box display="flex" flexDirection="column" flexGrow={1} padding="16px" border="1px solid #0000003B">
      <Box display="flex" alignItems="center" justifyContent="space-between">
        <Typography variant="h6" mb="6px">
          {title}
        </Typography>
        {id && (
          <Stack direction="row" spacing={1} alignItems="center">
            <ModeEditIcon
              cursor="pointer"
              onClick={() => {
                navigate('/settings/my-company/edit');
              }}
            />
            <LinkIcon
              cursor="pointer"
              onClick={() => {
                navigate(`/settings/company/${id}/connections`);
              }}
            />
          </Stack>
        )}
      </Box>
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
};
export const OverviewTab: React.FC<CompanyDetailsTabProps> = ({ companyDetails }) => {
  const companyInfo = {
    title: 'Company Information',
    id: companyDetails.id,
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
      { field: 'Total Sites', value: companyDetails.total_sites },
      { field: 'Projects Placed in Service', value: companyDetails.sites_placed_in_service },
      { field: 'Projects Under Construction', value: companyDetails.sites_under_construction },
      { field: 'Projects Sold', value: companyDetails.sites_sold },
      { field: 'Projects Decommissioned', value: companyDetails.sites_decommissioned },
      { field: 'System Size', value: formatFloatValue(companyDetails.total_capacity) }
    ]
  };

  return (
    <Box paddingTop={1} sx={{ flexGrow: 1 }}>
      <Grid container spacing={2}>
        <Grid item xs={12} md={6} lg={4}>
          <InfoBox title={companyInfo.title} infoTableData={companyInfo.infoTableData} id={companyInfo.id} />
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <Box display="flex" flexGrow={1}>
            <InfoBox title={sitesSummary.title} infoTableData={sitesSummary.infoTableData} />
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
};

export default OverviewTab;

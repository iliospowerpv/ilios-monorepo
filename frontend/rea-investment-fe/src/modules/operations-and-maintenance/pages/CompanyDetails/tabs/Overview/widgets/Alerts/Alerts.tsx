import React from 'react';
import dayjs from 'dayjs';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import BoltRoundedIcon from '@mui/icons-material/BoltRounded';
import WarningRoundedIcon from '@mui/icons-material/WarningRounded';
import Link from '@mui/material/Link';
import { WidgetContainer } from '../../Overview.style';
import { Link as RouterLink } from 'react-router-dom';
import utc from 'dayjs/plugin/utc';
import Tooltip from '@mui/material/Tooltip';
dayjs.extend(utc);

interface AlertsProps {
  companyId: number;
  title: string;
  data?: {
    id: number;
    severity: string;
    alert_start: string;
    type: string;
  }[];
}

const Alerts: React.FC<AlertsProps> = ({ companyId, title, data }) => {
  const formatDate = (date: string) => {
    return dayjs.utc(date).local().format('DD MMM, h:mm A');
  };

  if (!data) return null;

  return (
    <WidgetContainer>
      <Typography variant="h6" mb="6px">
        {title}
      </Typography>
      <Table sx={{ width: '100%' }} size="small">
        <TableBody>
          {data.map(({ severity, alert_start, type }, index) => (
            <TableRow
              key={`alerts-${severity}-${index}`}
              sx={{ '& .MuiTableCell-root': { px: 0, pb: 0, pt: 1, border: 'none' } }}
            >
              <TableCell
                sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                component="th"
                scope="row"
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {severity === 'Critical' && <BoltRoundedIcon sx={{ color: theme => theme.alertSeverity.severe }} />}
                  {severity === 'Warning' && <WarningRoundedIcon sx={{ color: theme => theme.alertSeverity.high }} />}
                  {severity === 'Informational' && (
                    <WarningRoundedIcon sx={{ color: theme => theme.alertSeverity.warning }} />
                  )}
                  <span>{formatDate(alert_start)}</span>
                  <Tooltip title={type} placement="top-start">
                    <Typography
                      variant="body2"
                      sx={{
                        flexGrow: 1,
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        cursor: 'pointer'
                      }}
                    >
                      {type}
                    </Typography>
                  </Tooltip>
                </Box>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {data?.length !== 0 ? (
        <Link
          component={RouterLink}
          to={`/operations-and-maintenance/companies/${companyId}/alerts`}
          underline="none"
          sx={{ fontWeight: 600, fontSize: '13px', marginTop: '15px' }}
        >
          See All Alerts
        </Link>
      ) : (
        <Box textAlign="center" mt="8px">
          Everything is running smoothly. There are currently no active alerts for your company
        </Box>
      )}
    </WidgetContainer>
  );
};

export default Alerts;

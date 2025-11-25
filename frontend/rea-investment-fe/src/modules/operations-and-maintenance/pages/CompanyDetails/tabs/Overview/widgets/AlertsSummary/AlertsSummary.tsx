import React from 'react';
import Typography from '@mui/material/Typography';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import { WidgetContainer } from '../../Overview.style';

interface AlertsSummaryProps {
  title: string;
  data?: {
    severity: string;
    total: number;
    unaccomplished_tasks_count: number;
  }[];
}

const AlertsSummary: React.FC<AlertsSummaryProps> = ({ title, data }) => {
  if (!data) return null;

  const defaultData = [
    { severity: 'critical', total: 0, unaccomplished_tasks_count: 0 },
    { severity: 'high', total: 0, unaccomplished_tasks_count: 0 },
    { severity: 'warning', total: 0, unaccomplished_tasks_count: 0 }
  ];

  const alertData = data?.length ? data : defaultData;

  return (
    <WidgetContainer>
      <Typography variant="h6" mb="6px">
        {title}
      </Typography>
      <Table sx={{ width: '100%' }} size="small">
        <TableBody>
          <TableRow sx={{ '& .MuiTableCell-root': { px: 0, pb: 0, pt: 1, border: 'none' } }}>
            <TableCell component="th"></TableCell>
            <TableCell component="th" sx={{ color: theme => theme.palette.text.secondary }}>
              Active
            </TableCell>
            <TableCell component="th" sx={{ color: theme => theme.palette.text.secondary }}>
              Task Created
            </TableCell>
          </TableRow>
          {alertData.map(({ severity, total, unaccomplished_tasks_count }, index) => (
            <TableRow
              key={`alerts-summary-${severity}-${index}`}
              sx={{ '& .MuiTableCell-root': { px: 0, pb: 0, pt: 1, border: 'none' } }}
            >
              <TableCell component="th" sx={{ textTransform: 'capitalize' }}>
                {severity}
              </TableCell>
              <TableCell component="th">{total}</TableCell>
              <TableCell component="th">{unaccomplished_tasks_count}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </WidgetContainer>
  );
};

export default AlertsSummary;

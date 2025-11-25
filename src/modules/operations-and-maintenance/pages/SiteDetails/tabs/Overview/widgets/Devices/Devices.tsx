import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import { WidgetWrapper } from '../../Overview.style';
import { ApiClient } from '../../../../../../../../api';

interface DevicesProps {
  siteId: number;
}

const Devices: React.FC<DevicesProps> = ({ siteId }) => {
  const {
    data: { data } = { data: [] },
    isFetching,
    error,
    refetch
  } = useQuery({
    queryFn: () => ApiClient.operationsAndMaintenance.siteDevicesOverviewSection(siteId),
    queryKey: ['sites', 'devices-status-overview', { siteId }],
    staleTime: 15 * 60 * 1000,
    refetchInterval: 15 * 60 * 1000
  });

  return (
    <WidgetWrapper
      title="Devices"
      isLoading={isFetching}
      error={!!error}
      errorMsg={(error instanceof AxiosError && error.response?.data?.message) || error?.message}
      onClickRefetch={refetch}
    >
      <Table sx={{ width: '100%' }} size="small">
        <TableBody>
          <TableRow sx={{ '& .MuiTableCell-root': { px: 0, pb: 0, pt: 1, border: 'none' } }}>
            <TableCell component="th"></TableCell>
            <TableCell component="th" sx={{ color: theme => theme.palette.text.secondary }}>
              Devices
            </TableCell>
            <TableCell component="th" sx={{ color: theme => theme.palette.text.secondary }}>
              Critical Errors
            </TableCell>
            <TableCell component="th" sx={{ color: theme => theme.palette.text.secondary }}>
              Not Responding
            </TableCell>
          </TableRow>
          {data.map(({ critical_errors, device_type, devices, no_respond }) => (
            <TableRow key={device_type} sx={{ '& .MuiTableCell-root': { px: 0, pb: 0, pt: 1, border: 'none' } }}>
              <TableCell component="th" sx={{ textTransform: 'capitalize' }}>
                {device_type}
              </TableCell>
              <TableCell component="th">{devices}</TableCell>
              <TableCell component="th">{critical_errors}</TableCell>
              <TableCell component="th">{no_respond}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </WidgetWrapper>
  );
};

export default Devices;

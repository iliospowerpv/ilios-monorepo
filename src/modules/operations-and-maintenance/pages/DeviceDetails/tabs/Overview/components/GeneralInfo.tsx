import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Link from '@mui/material/Link';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';

import { DeviceDetailsTabProps } from '../../types';

interface GeneralInfoProps {
  data: DeviceDetailsTabProps['deviceDetails']['general_info'];
}

export const GeneralInfo: React.FC<GeneralInfoProps> = ({ data }) => {
  const infoTableData: {
    field: string;
    value: string | number | null;
    valueType?: 'plain' | 'hyperlink';
  }[] = [
    { field: 'Status', value: data.status },
    { field: 'Device Name', value: data.name },
    { field: 'Asset ID', value: data.asset_id },
    { field: 'Device Category', value: data.category },
    { field: 'Device Type', value: data.type },
    { field: 'Manufacturer', value: data.manufacturer },
    { field: 'Model', value: data.model },
    { field: 'Serial # / Asset Tag', value: data.serial_number },
    { field: 'Warranty Effective Date', value: data.warranty_effective_date },
    { field: 'Warranty Term', value: data.warranty_term },
    { field: 'Gateway ID', value: data.gateway_id },
    { field: 'Function ID', value: data.function_id },
    { field: 'Driver', value: data.driver },
    { field: 'Install Date', value: data.install_date },
    { field: 'Decommissioned Date', value: data.decommissioned_date },
    { field: 'Last Updated', value: data.last_updated_date }
  ];

  return (
    <Box display="flex" flexDirection="column" flexGrow={1} padding="16px" border="1px solid #0000003B">
      <Typography variant="h6" mb="6px">
        General Device Information
      </Typography>
      <Table sx={{ width: '100%', height: 'auto', tableLayout: 'fixed' }} size="small">
        <TableBody>
          {infoTableData.map(({ field, value, valueType }) => (
            <TableRow key={field} sx={{ '& .MuiTableCell-root': { px: 0, pb: 0, pt: 1, border: 'none' } }}>
              <TableCell component="th" scope="row" sx={{ fontWeight: 600 }}>
                {`${field}:`}
              </TableCell>
              <TableCell align="right">
                {valueType === 'hyperlink' && typeof value === 'string' ? (
                  <Box
                    sx={{
                      overflow: 'hidden',
                      whiteSpace: 'nowrap',
                      textOverflow: 'ellipsis'
                    }}
                  >
                    <Link href={value} rel="noreferrer" target="_blank">
                      {value}
                    </Link>
                  </Box>
                ) : typeof value !== 'number' ? (
                  value || '-'
                ) : (
                  value
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
};

export default GeneralInfo;

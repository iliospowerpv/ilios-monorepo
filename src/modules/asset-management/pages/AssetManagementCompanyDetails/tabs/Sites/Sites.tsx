import React from 'react';

import SitesTable from '../../../../../../components/common/tables/SitesTable/SitesTable';
import { AssetManagementCompanyDetailsTabProps } from '../types';
import Chip from '@mui/material/Chip';
import formatFloatValue from '../../../../../../utils/formatters/formatFloatValue';

const columns = [
  {
    headerName: 'Site Name',
    field: 'name',
    flex: 1,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'Status',
    field: 'status',
    flex: 1,
    cellRenderer: (params: { data: { status: 'Construction' | 'Placed in Service' | 'Decommissioned' | 'Sold' } }) => {
      const statusColors: Record<typeof params.data.status, string> = {
        Construction: '#FAE353',
        'Placed in Service': '#85CE83',
        Decommissioned: '#B02E0C',
        Sold: '#86D0FD'
      };
      const getColorForStatus = (status: typeof params.data.status): string => statusColors[status];
      return params.data.status ? (
        <Chip
          label={params.data.status}
          color="success"
          size="small"
          sx={theme => ({
            color: theme.palette.primary.main,
            background: getColorForStatus(params.data.status)
          })}
        />
      ) : null;
    },
    sortable: false,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'Ownership Structure',
    field: 'ownership_structure',
    flex: 1,
    sortable: false,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'Address',
    field: 'address',
    flex: 1,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'City',
    field: 'city',
    flex: 1,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'State',
    field: 'state',
    flex: 1,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'System Size kW (DC)',
    field: 'system_size_dc',
    flex: 1,
    checked: true,
    isDefault: true,
    cellRenderer: (data: any) => {
      return typeof data?.value === 'number' ? formatFloatValue(data.value) : '';
    }
  },
  {
    headerName: 'Placed in Service Date',
    field: 'placed_in_service_date',
    flex: 1,
    sortable: false,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'Production Guarantee',
    field: 'production_guarantee',
    flex: 1,
    sortable: false,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'O&M Provider',
    field: 'o_and_m_provider',
    flex: 1,
    sortable: false,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'Utility Provider',
    field: 'utility_provider',
    flex: 1,
    sortable: false,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'EPC Provider',
    field: 'epc_provider',
    flex: 1,
    sortable: false,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'Zip Code',
    field: 'zip_code',
    flex: 1,
    checked: false,
    isDefault: false
  },
  {
    headerName: 'County',
    field: 'county',
    flex: 1,
    checked: false,
    isDefault: false
  },
  {
    headerName: 'Latitude/Longitude',
    field: 'lon_lat_url',
    flex: 1,
    checked: false,
    isDefault: false
  },
  {
    headerName: 'System Size kW (AC)',
    field: 'system_size_ac',
    flex: 1,
    checked: false,
    isDefault: false,
    cellRenderer: (data: any) => {
      return typeof data?.value === 'number' ? formatFloatValue(data.value) : '';
    }
  },
  {
    headerName: 'Data Acquisition System Provider',
    field: 'das_provider',
    flex: 1,
    checked: false,
    isDefault: false,
    sortable: false
  }
];

const SitesTab: React.FC<AssetManagementCompanyDetailsTabProps> = ({ companyDetails }) => (
  <SitesTable columns={columns} companyId={companyDetails.id} />
);

export default SitesTab;

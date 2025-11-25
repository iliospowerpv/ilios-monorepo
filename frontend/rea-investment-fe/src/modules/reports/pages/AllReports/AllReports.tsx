import React, { useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import EmptyReport from '../../components/EmptyReport';
import { DeviceForm, DeviceFormFields } from '../../components/GenerateReportForm';
import Button from '@mui/material/Button';
import DownloadIcon from '@mui/icons-material/Download';
import PowerBIReport from '../../components/PowerBIReport';
import { ApiClient } from '../../../../api';
import { useNotify } from '../../../../contexts/notifications/notifications';
import FullPageLoader from '../../../../components/common/FullPageLoader/FullPageLoader';

export const AllReportsPage: React.FC = () => {
  const [filters, setFilters] = useState<DeviceFormFields>();
  const [loading, setLoading] = useState<boolean>(false);
  const notify = useNotify();

  async function exportPowerBIReportToPDF(reportId: string) {
    try {
      notify('The PDF export has started.');
      setLoading(true);
      const pages = await ApiClient.reports.getPages(reportId);
      const powerBIReportConfiguration = {
        pages: pages?.value?.map(page => ({ pageName: page.name })),
        reportLevelFilters: [
          {
            filter: `DimDate/Date ge ${filters?.start_date} and DimDate/Date le ${filters?.end_date} and DimSite/SiteId eq ${filters?.site?.id}`
          }
        ]
      };
      const body = {
        format: 'PDF',
        powerBIReportConfiguration: powerBIReportConfiguration
      };
      const startExportRes = await ApiClient.reports.exportToFile(reportId, body);
      const { id: exportId } = startExportRes;
      let exportStatus = 'Running';

      while (['Running', 'NotStarted'].includes(exportStatus)) {
        await delay(2000);
        const statusRes = await ApiClient.reports.getStatus(reportId, exportId);
        exportStatus = statusRes?.status;
      }

      if (exportStatus !== 'Succeeded') {
        notify(`Export failed with status: ${exportStatus}`);
        throw new Error(`Export failed with status: ${exportStatus}`);
      }

      const fileBlob = await ApiClient.reports.getFile(reportId, exportId);
      downloadBlob(
        fileBlob,
        `${filters?.type?.name}_${filters?.company?.name}_${filters?.site?.name}_${filters?.end_date}.pdf`
      );

      notify('PDF download completed.');
    } catch (error) {
      notify(`Something went wrong: ${error}`);
      throw error;
    } finally {
      setLoading(false);
    }
  }

  const delay = (ms: number) => new Promise(res => setTimeout(res, ms));

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  return (
    <Box maxWidth="1600px" mx="auto">
      <FullPageLoader open={loading} />
      <Box display="flex" flexDirection={'row'} justifyContent="space-between">
        <Typography variant="h4" sx={{ fontWeight: 600 }} fontSize="34px" lineHeight="42px">
          Reports
        </Typography>
        <Button
          onClick={() => exportPowerBIReportToPDF(filters?.type?.id ? filters?.type?.id : '')}
          fullWidth
          disabled={!filters?.type?.id || loading}
          variant="outlined"
          sx={{ maxWidth: '200px', width: '100%' }}
        >
          <DownloadIcon sx={{ paddingRight: '8px' }} />
          Export Report
        </Button>
      </Box>
      <Box sx={{ paddingTop: '24px' }}>
        <Box>
          <DeviceForm onFilterChange={setFilters} />
        </Box>
        {!filters?.site ? <EmptyReport /> : <PowerBIReport filters={filters} />}
      </Box>
    </Box>
  );
};

export default AllReportsPage;

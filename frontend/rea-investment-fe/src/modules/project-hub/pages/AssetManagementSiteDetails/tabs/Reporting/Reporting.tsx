import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useForm, SubmitHandler, Controller } from 'react-hook-form';
import { models, Report } from 'powerbi-client';
import { PowerBIEmbed } from 'powerbi-client-react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import { SearchableSelect } from '../../../../../../components/common/SearchableSelect/SearchableSelect';
import CircularProgress from '@mui/material/CircularProgress';
import AssessmentIcon from '@mui/icons-material/Assessment';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { DesktopDatePicker } from '@mui/x-date-pickers/DesktopDatePicker';
import dayjs from 'dayjs';
import CustomParseFormatPlugin from 'dayjs/plugin/customParseFormat';

import type { AssetManagementSiteDetailsTabProps } from '../types';
import { ApiClient } from '../../../../../../api';


dayjs.extend(CustomParseFormatPlugin);

interface ReportType {
  id: string;
  name: string;
  web_url: string;
  embed_url: string;
}

interface ReportFormFields {
  type: ReportType;
  start_date: dayjs.Dayjs;
  end_date: dayjs.Dayjs;
}

interface ProjectHubReportFilters {
  company: { id: string; name: string };
  site: { id: string; name: string };
  type: ReportType;
  start_date: string;
  end_date: string;
}

const ProjectHubPowerBIReport: React.FC<{ filters: ProjectHubReportFilters }> = ({ filters }) => {
  const reportId = filters?.type?.id;
  const reportRef = useRef<Report | null>(null);
  const [reportConfig, setReportConfig] = useState<models.IReportEmbedConfiguration>({
    type: 'report',
    embedUrl: '',
    accessToken: '',
    id: '',
    tokenType: models.TokenType.Embed,
    settings: {
      panes: {},
      navContentPaneEnabled: false,
      background: models.BackgroundType.Transparent
    }
  });

  const { data: tokenData, isLoading } = useQuery({
    queryFn: () => ApiClient.reports.getReportToken(reportId || ''),
    queryKey: ['reports-token', { reportId }],
    staleTime: 0,
    enabled: !!reportId
  });

  useEffect(() => {
    if (tokenData && filters) {
      setReportConfig(prevConfig => ({
        ...prevConfig,
        embedUrl: `${filters.type.embed_url}&filter=DimDate/Date%20ge%20${filters.start_date}%20and%20DimDate/Date%20le%20${filters.end_date}%20and%20DimSite/SiteId%20eq%20${filters.site.id}`,
        accessToken: tokenData.embed_token,
        id: reportId
      }));
    }
  }, [tokenData, filters, reportId]);

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box marginTop="20px">
      <PowerBIEmbed
        embedConfig={reportConfig}
        cssClassName="power-bi-report-class"
        getEmbeddedComponent={embeddedReport => {
          reportRef.current = embeddedReport as Report;
        }}
      />
    </Box>
  );
};

const EmptyReportState: React.FC = () => (
  <Card variant="outlined" sx={{ mt: 3 }}>
    <CardContent sx={{ textAlign: 'center', py: 6 }}>
      <AssessmentIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
      <Typography variant="h6" color="text.secondary" gutterBottom>
        Select Report Parameters
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Choose a report type and date range, then click &quot;Generate Report&quot; to view analytics for this project.
      </Typography>
    </CardContent>
  </Card>
);

export const Reporting: React.FC<AssetManagementSiteDetailsTabProps> = ({ siteDetails }) => {
  const navigate = useNavigate();
  const { siteId: routeSiteId } = useParams<{ siteId: string }>();
  const [filters, setFilters] = useState<ProjectHubReportFilters | undefined>();

  const siteId = routeSiteId ? Number(routeSiteId) : siteDetails.id;

  const { handleSubmit, formState, control, watch } = useForm<ReportFormFields>({
    mode: 'onBlur',
    criteriaMode: 'all',
    reValidateMode: 'onBlur',
    defaultValues: {
      type: undefined,
      start_date: undefined,
      end_date: undefined
    }
  });

  const { data: reportsResponseData, isLoading: reportsLoading } = useQuery({
    queryFn: () => ApiClient.reports.getReportsOption(),
    queryKey: ['reports-options']
  });

  const onSubmit: SubmitHandler<ReportFormFields> = async data => {
    const selectedReport = data.type;
    if (!selectedReport) return;

    const startDate = dayjs(data.start_date).startOf('month').format('YYYY-MM-DD');
    const selectedEndDate = dayjs(data.end_date);
    const now = dayjs();
    const isCurrentMonth = selectedEndDate.isSame(now, 'month');
    const endDate = isCurrentMonth ? now.format('YYYY-MM-DD') : selectedEndDate.endOf('month').format('YYYY-MM-DD');

    setFilters({
      company: {
        id: String(siteDetails.company.id),
        name: siteDetails.company.name
      },
      site: {
        id: String(siteId),
        name: siteDetails.name
      },
      type: selectedReport,
      start_date: startDate,
      end_date: endDate
    });
  };

  const handleOpenGlobalReports = () => {
    navigate('/reports');
  };

  const { errors, isValid, isSubmitting, isDirty } = formState;
  const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43, height: '40px' };

  const startDate = watch('start_date');
  const endDate = watch('end_date');
  const today = dayjs();
  const baseMin = dayjs(new Date(2022, 0, 1));
  const maxDate = endDate && dayjs(endDate).isBefore(today) ? dayjs(endDate) : today;
  const minDate = startDate && dayjs(startDate).isAfter(baseMin) ? dayjs(startDate) : baseMin;

  if (reportsLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="300px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
        <Box display="flex" alignItems="center" gap={1}>
          <AssessmentIcon color="primary" />
          <Typography variant="h5" sx={{ fontWeight: 500 }}>
            Project Reports
          </Typography>
          <Chip label={siteDetails.name} size="small" color="primary" variant="outlined" sx={{ ml: 1 }} />
        </Box>
        <Button variant="outlined" startIcon={<OpenInNewIcon />} onClick={handleOpenGlobalReports}>
          Open Global Reports
        </Button>
      </Box>

      <Alert severity="info" sx={{ mb: 3 }}>
        Reports are pre-filtered to this project ({siteDetails.name}). Select a report type and date range below.
      </Alert>

      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Stack
            direction={{ xs: 'column', md: 'row' }}
            component="form"
            noValidate
            spacing={2}
            onSubmit={handleSubmit(onSubmit)}
            alignItems="flex-start"
          >
            <Box sx={{ minWidth: '200px' }}>
              <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>
                Project (Locked)
              </Typography>
              <Chip label={siteDetails.name} sx={{ height: '40px', borderRadius: 1 }} />
            </Box>

            <Box sx={{ minWidth: '200px' }}>
              <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>
                Report Type
              </Typography>
              <Controller
                name="type"
                control={control}
                rules={{ required: 'Report type is required' }}
                render={({ field }) => (
                  <SearchableSelect
                    options={(reportsResponseData?.items || []).map(report => ({
                      label: report.name,
                      value: report.id
                    }))}
                    value={(field.value as ReportType | undefined)?.id || null}
                    onChange={val => {
                      const report = reportsResponseData?.items.find(r => r.id === val);
                      field.onChange(report ?? undefined);
                    }}
                    onBlur={field.onBlur}
                    inputRef={field.ref}
                    label="Select Report"
                    error={!!errors.type}
                    required
                    disabled={field.disabled}
                    variant="outlined"
                    size="small"
                    placeholder="Select Report"
                    sx={{ minWidth: 200 }}
                  />
                )}
              />
            </Box>

            <Box sx={{ minWidth: '160px' }}>
              <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>
                From
              </Typography>
              <Controller
                name="start_date"
                control={control}
                rules={{ required: 'Start date is required' }}
                render={({ field: { ref, value, onChange, ...field } }) => (
                  <DesktopDatePicker
                    {...field}
                    value={value || null}
                    views={['year', 'month']}
                    format="MM/YYYY"
                    inputRef={ref}
                    minDate={dayjs(new Date(2022, 0, 1))}
                    maxDate={maxDate || undefined}
                    onChange={val => onChange(val)}
                    slotProps={{
                      textField: {
                        placeholder: 'Start',
                        error: !!errors.start_date,
                        size: 'small',
                        fullWidth: true,
                        InputProps: { sx: inputStyles },
                        variant: 'outlined'
                      }
                    }}
                  />
                )}
              />
            </Box>

            <Box sx={{ minWidth: '160px' }}>
              <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>
                To
              </Typography>
              <Controller
                name="end_date"
                control={control}
                rules={{ required: 'End date is required' }}
                render={({ field: { ref, value, onChange, ...field } }) => (
                  <DesktopDatePicker
                    {...field}
                    value={value || null}
                    views={['year', 'month']}
                    format="MM/YYYY"
                    inputRef={ref}
                    minDate={minDate || undefined}
                    maxDate={today}
                    onChange={val => onChange(val)}
                    slotProps={{
                      textField: {
                        placeholder: 'End',
                        error: !!errors.end_date,
                        size: 'small',
                        fullWidth: true,
                        InputProps: { sx: inputStyles },
                        variant: 'outlined'
                      }
                    }}
                  />
                )}
              />
            </Box>

            <Box sx={{ minWidth: '150px', pt: 2.5 }}>
              <Button disabled={!isValid || !isDirty || isSubmitting} fullWidth variant="contained" type="submit">
                Generate Report
              </Button>
            </Box>
          </Stack>
        </CardContent>
      </Card>

      {filters ? <ProjectHubPowerBIReport filters={filters} /> : <EmptyReportState />}
    </Box>
  );
};

export default Reporting;

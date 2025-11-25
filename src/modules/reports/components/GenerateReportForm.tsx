import React, { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useForm, SubmitHandler, Controller } from 'react-hook-form';
import Stack from '@mui/material/Stack';
import CompanySearchField from './CompanySearchField';
import SiteSearchField from './SiteSearchField';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import { DesktopDatePicker } from '@mui/x-date-pickers/DesktopDatePicker';
import dayjs from 'dayjs';
import CustomParseFormatPlugin from 'dayjs/plugin/customParseFormat';
import { StyledSelectItem } from '../../asset-management/pages/DeviceDetails/tabs/Overview/components/TechnicalDetailCard/TechnicalDetail.styles';
import FormControl from '@mui/material/FormControl';
import Select from '@mui/material/Select';
import { useTheme } from '@mui/material/styles';
import { ApiClient } from '../../../api';
dayjs.extend(CustomParseFormatPlugin);

interface Type {
  id: string;
  name: string;
  web_url: string;
  embed_url: string;
}

export type DeviceFormFields = {
  company: CompanyType;
  site: CompanyType | null;
  type: Type;
  start_date: string;
  end_date: string;
};

interface CompanyType {
  id: string;
  name: string;
}

interface DeviceFormProps {
  onFilterChange: (newFilters: DeviceFormFields | undefined) => void;
}

export const DeviceForm: React.FC<DeviceFormProps> = ({ onFilterChange }) => {
  const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43, height: '40px' };
  const theme = useTheme();
  const { handleSubmit, formState, control, watch, reset, getValues, setValue } = useForm<DeviceFormFields>({
    mode: 'onBlur',
    criteriaMode: 'all',
    reValidateMode: 'onBlur',
    defaultValues: {
      company: undefined,
      site: undefined,
      type: undefined,
      start_date: undefined,
      end_date: undefined
    }
  });

  const { data: reportsResponseData } = useQuery({
    queryFn: () => ApiClient.reports.getReportsOption(),
    queryKey: ['reports-options']
  });

  const onSubmit: SubmitHandler<DeviceFormFields> = async data => {
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    const selectedReport = reportsResponseData?.items.find(report => report.id === data.type);
    const filters = data;
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    filters.type = selectedReport;
    filters.start_date = dayjs(data.start_date, 'YYYY-MM-DD', true).startOf('month').format('YYYY-MM-DD');
    const selectedDate = dayjs(data.end_date);
    const now = dayjs();
    const isCurrentMonth = selectedDate.isSame(now, 'month');
    filters.end_date = isCurrentMonth ? now.format('YYYY-MM-DD') : selectedDate.endOf('month').format('YYYY-MM-DD');
    onFilterChange(filters);
    reset(getValues());
  };

  const { errors, isValid, isSubmitting, isDirty } = formState;
  const company: CompanyType | undefined = watch('company');
  const companyId: string | undefined = company?.id;

  const previousCompany = useRef<CompanyType | undefined>(undefined);

  useEffect(() => {
    if (!company) {
      setValue('site', null);
      reset(getValues());
    }
    if (previousCompany?.current?.name !== null && previousCompany.current?.name !== company?.name) {
      setValue('site', null);
      reset(getValues());
    }
    previousCompany.current = company;
  }, [company, setValue, getValues, reset]);

  const startDate = watch('start_date');
  const endDate = watch('end_date');
  const today = dayjs();
  const baseMin = dayjs(new Date(2022, 0, 1));
  // eslint-disable-next-line @typescript-eslint/ban-ts-comment
  // @ts-ignore
  const maxDate = endDate && endDate.isBefore(today) ? endDate : today;
  // eslint-disable-next-line @typescript-eslint/ban-ts-comment
  // @ts-ignore
  const minDate = startDate && startDate.isAfter(baseMin) ? startDate : baseMin;

  return (
    <Stack direction="row" component="form" noValidate spacing={2} onSubmit={handleSubmit(onSubmit)}>
      <Box sx={{ maxWidth: '280px', width: '100%' }}>
        <Controller
          name="company"
          control={control}
          rules={{
            required: 'Company is required field'
          }}
          render={({ field: { ref, value, onChange, ...field } }) => (
            <CompanySearchField {...field} value={value} onChange={(_, newValue) => onChange(newValue)} ref={ref} />
          )}
        />
      </Box>
      <Box sx={{ maxWidth: '280px', width: '100%' }}>
        <Controller
          name="site"
          control={control}
          rules={{
            required: 'Site is required field'
          }}
          render={({ field: { ref, value, onChange, ...field } }) => (
            <SiteSearchField
              {...field}
              value={value}
              onChange={(_, newValue) => onChange(newValue)}
              ref={ref}
              company={companyId ? companyId : ''}
              disabled={!companyId}
            />
          )}
        />
      </Box>
      <Box sx={{ maxWidth: '200px', width: '100%' }}>
        <Controller
          name="type"
          control={control}
          rules={{
            required: 'Report type is required field'
          }}
          render={({ field }) => (
            <FormControl error={!!errors.type} required sx={{ minWidth: 200 }}>
              <Select
                inputRef={field.ref}
                value={field.value || ''}
                error={!!errors.type}
                disabled={field.disabled}
                onChange={field.onChange}
                fullWidth
                variant="outlined"
                size="small"
                displayEmpty
              >
                <StyledSelectItem value="">
                  <Box sx={{ color: theme.palette.text.disabled }}>Report Type</Box>
                </StyledSelectItem>
                {reportsResponseData &&
                  reportsResponseData.items.map(status => (
                    <StyledSelectItem key={status.id} value={status.id}>
                      {status.name}
                    </StyledSelectItem>
                  ))}
              </Select>
            </FormControl>
          )}
        />
      </Box>
      <Box sx={{ maxWidth: '280px', width: '100%' }}>
        <Controller
          name="start_date"
          control={control}
          rules={{
            required: 'Start Date is required field'
          }}
          render={({ field: { ref, value, onChange, ...field } }) => (
            <DesktopDatePicker
              {...field}
              value={value}
              views={['year', 'month']}
              format="MM/YYYY"
              inputRef={ref}
              minDate={dayjs(new Date(2022, 0, 1))}
              maxDate={maxDate || undefined}
              onChange={val => onChange(val)}
              slotProps={{
                textField: {
                  placeholder: 'From',
                  error: !!errors.start_date,
                  helperText: errors.start_date?.message,
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
      <Box sx={{ maxWidth: '280px', width: '100%' }}>
        <Controller
          name="end_date"
          control={control}
          rules={{
            required: 'End Date is required field'
          }}
          render={({ field: { ref, value, onChange, ...field } }) => (
            <DesktopDatePicker
              {...field}
              value={value}
              views={['year', 'month']}
              format="MM/YYYY"
              inputRef={ref}
              minDate={minDate || undefined}
              maxDate={today}
              onChange={val => onChange(val)}
              slotProps={{
                textField: {
                  placeholder: 'To',
                  error: !!errors.end_date,
                  helperText: errors.end_date?.message,
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
      <Button
        disabled={!isValid || !isDirty || isSubmitting}
        fullWidth
        variant="contained"
        type="submit"
        sx={{ maxWidth: '200px', width: '100%' }}
      >
        Generate Report
      </Button>
    </Stack>
  );
};

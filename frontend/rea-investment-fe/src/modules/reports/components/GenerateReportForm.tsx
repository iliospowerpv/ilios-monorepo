import React, { useEffect, useRef, useState } from 'react';
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
import { SearchableSelect } from '../../../components/common/SearchableSelect/SearchableSelect';
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
  const [startOpen, setStartOpen] = useState(false);
  const [endOpen, setEndOpen] = useState(false);
  const { handleSubmit, formState, control, watch, reset, getValues, setValue } = useForm<DeviceFormFields>({
    mode: 'onBlur',
    criteriaMode: 'all',
    reValidateMode: 'onBlur',
    defaultValues: {
      company: undefined,
      site: undefined,
      type: undefined,
      start_date: null as any,
      end_date: null as any
    }
  });

  const { data: reportsResponseData } = useQuery({
    queryFn: () => ApiClient.reports.getReportsOption(),
    queryKey: ['reports-options']
  });

  const onSubmit: SubmitHandler<DeviceFormFields> = async data => {
    const filters = data;
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
            required: 'Project is required field'
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
            <SearchableSelect
              options={(reportsResponseData?.items || []).map(report => ({
                label: report.name,
                value: report.id
              }))}
              value={(field.value as Type | undefined)?.id || null}
              onChange={val => {
                const report = reportsResponseData?.items.find(r => r.id === val);
                field.onChange(report ?? undefined);
              }}
              onBlur={field.onBlur}
              inputRef={field.ref}
              label="Report Type"
              error={!!errors.type}
              required
              disabled={field.disabled}
              variant="outlined"
              size="small"
              placeholder="Report Type"
              sx={{ minWidth: 200 }}
            />
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
              views={['year', 'month', 'day']}
              format="MM/DD/YYYY"
              inputRef={ref}
              minDate={dayjs(new Date(2022, 0, 1))}
              maxDate={maxDate || undefined}
              onChange={val => onChange(val)}
              open={startOpen}
              onOpen={() => setStartOpen(true)}
              onClose={() => setStartOpen(false)}
              slotProps={{
                textField: {
                  placeholder: 'From',
                  error: !!errors.start_date,
                  helperText: errors.start_date?.message,
                  size: 'small',
                  fullWidth: true,
                  InputProps: { sx: inputStyles },
                  variant: 'outlined',
                  onClick: () => setStartOpen(true)
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
              views={['year', 'month', 'day']}
              format="MM/DD/YYYY"
              inputRef={ref}
              minDate={minDate || undefined}
              maxDate={today}
              onChange={val => onChange(val)}
              open={endOpen}
              onOpen={() => setEndOpen(true)}
              onClose={() => setEndOpen(false)}
              slotProps={{
                textField: {
                  placeholder: 'To',
                  error: !!errors.end_date,
                  helperText: errors.end_date?.message,
                  size: 'small',
                  fullWidth: true,
                  InputProps: { sx: inputStyles },
                  variant: 'outlined',
                  onClick: () => setEndOpen(true)
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

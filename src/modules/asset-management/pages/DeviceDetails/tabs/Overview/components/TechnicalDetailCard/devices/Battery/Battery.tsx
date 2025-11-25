import React from 'react';
import dayjs, { Dayjs } from 'dayjs';
import CustomParseFormatPlugin from 'dayjs/plugin/customParseFormat';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import TableRow from '@mui/material/TableRow';
import TableBody from '@mui/material/TableBody';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';

import FormattedNumericInput from '../../../../../../../../../../components/common/FormattedNumericInput/FormattedNumericInput';
import { FieldCell, TextBox, SectionTable, StyledSelectItem } from '../../TechnicalDetail.styles';
import { DeviceTechnicalDetailsFormProps, DeviceTechnicalDetailsFormRef } from '../../TechnicalDetailCard';
import formatFloatValue from '../../../../../../../../../../utils/formatters/formatFloatValue';
import { ApiClient, BatteryDeviceTechnicalDetails, TechnicalDetailAttributes } from '../../../../../../../../../../api';
import { useNotify } from '../../../../../../../../../../contexts/notifications/notifications';

dayjs.extend(CustomParseFormatPlugin);

interface BatteryFormFields {
  report: string | null;
  report_due_date: Dayjs | null;
  size_kw: string | null;
  size_mwh: string | null;
}

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

const Battery = React.forwardRef<DeviceTechnicalDetailsFormRef, DeviceTechnicalDetailsFormProps>(
  ({ mode, category, setMode, siteId, deviceId, technicalDetailsData: technicalDetailData, reflectFormState }, ref) => {
    const queryClient = useQueryClient();
    const notify = useNotify();

    const { handleSubmit, formState, control, reset } = useForm<BatteryFormFields>({
      mode: 'onChange',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        report:
          typeof technicalDetailData.report === 'number'
            ? formatFloatValue(technicalDetailData.report, true)
            : technicalDetailData.report,
        report_due_date: technicalDetailData.report_due_date
          ? dayjs(technicalDetailData.report_due_date, 'YYYY-MM-DD', true)
          : null,
        size_kw:
          typeof technicalDetailData.size_kw === 'number'
            ? formatFloatValue(technicalDetailData.size_kw, true)
            : technicalDetailData.size_kw,
        size_mwh:
          typeof technicalDetailData.size_mwh === 'number'
            ? formatFloatValue(technicalDetailData.size_mwh, true)
            : technicalDetailData.size_mwh
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateDeviceTechnicalDetails } = useMutation({
      mutationFn: (attributes: BatteryDeviceTechnicalDetails) => {
        const data: TechnicalDetailAttributes = {
          category: category,
          technical_details: attributes
        };

        return ApiClient.assetManagement.updateTechnicalDetails(deviceId, siteId, data);
      }
    });

    React.useEffect(() => {
      reflectFormState({
        isValid,
        isDirty,
        isSubmitting
      });
    }, [isValid, isSubmitting, isDirty, reflectFormState]);

    React.useEffect(() => {
      reset({
        report:
          typeof technicalDetailData.report === 'number'
            ? formatFloatValue(technicalDetailData.report, true)
            : technicalDetailData.report,
        report_due_date: technicalDetailData.report_due_date
          ? dayjs(technicalDetailData.report_due_date, 'YYYY-MM-DD', true)
          : null,
        size_kw:
          typeof technicalDetailData.size_kw === 'number'
            ? formatFloatValue(technicalDetailData.size_kw, true)
            : technicalDetailData.size_kw,
        size_mwh:
          typeof technicalDetailData.size_mwh === 'number'
            ? formatFloatValue(technicalDetailData.size_mwh, true)
            : technicalDetailData.size_mwh
      });
    }, [technicalDetailData, reset]);

    const onSubmit: SubmitHandler<BatteryFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateDeviceTechnicalDetails({
            report: data.report ?? null,
            report_due_date: data.report_due_date ? data.report_due_date.format('YYYY-MM-DD') : null,
            size_kw: data.size_kw ? Number.parseFloat(data.size_kw.replaceAll(',', '')) : null,
            size_mwh: data.size_mwh ? Number.parseFloat(data.size_mwh.replaceAll(',', '')) : null
          });
          notify(response.message || `Technical details was successfully updated.`);
          reset({
            report: data.report,
            report_due_date: data.report_due_date,
            size_kw: data.size_kw,
            size_mwh: data.size_mwh
          });
          queryClient.invalidateQueries({ queryKey: ['device'] });
          setMode('view');
        } catch (e: any) {
          notify(e.response?.data?.message || 'Something went wrong when updating the Technical details...');
        }
      },
      [notify, queryClient, reset, setMode, updateDeviceTechnicalDetails]
    );

    const handleFormSubmit = React.useMemo(() => handleSubmit(onSubmit), [handleSubmit, onSubmit]);

    React.useImperativeHandle(
      ref,
      () => ({
        resetForm: () => {
          reset();
        },
        submit: () => {
          handleFormSubmit();
        }
      }),
      [reset, handleFormSubmit]
    );

    return (
      <Box component="form">
        <SectionTable size="small">
          <TableBody>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Battery Size (kW - AC)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.size_kw !== null ? formatFloatValue(technicalDetailData.size_kw) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="size_kw"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Battery Size'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.size_kw}
                        helperText={errors.size_kw?.message}
                        disabled={isSubmitting}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          inputComponent: FormattedNumericInput as any,
                          ref: ref,
                          sx: inputStyles
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Battery Size (MWh - AC)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.size_mwh !== null ? formatFloatValue(technicalDetailData.size_mwh) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="size_mwh"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Battery Size'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.size_mwh}
                        helperText={errors.size_mwh?.message}
                        disabled={isSubmitting}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          inputComponent: FormattedNumericInput as any,
                          ref: ref,
                          sx: inputStyles
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Smart ESS Annual Report</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{technicalDetailData.report || ''}</TextBox>
                ) : (
                  <Controller
                    name="report"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.report}
                        helperText={errors.report?.message}
                        InputProps={{
                          sx: inputStyles
                        }}
                        select
                        fullWidth
                        variant="outlined"
                        size="small"
                      >
                        <StyledSelectItem value="Yes">Yes</StyledSelectItem>
                        <StyledSelectItem value="No">No</StyledSelectItem>
                      </TextField>
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Smart ESS Annual Report Due Date</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.report_due_date
                      ? dayjs(technicalDetailData.report_due_date, 'YYYY-MM-DD', true).format('MM/DD/YYYY')
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="report_due_date"
                    control={control}
                    rules={{
                      validate: value => {
                        if (value === null) return true;
                        if (!dayjs(value).isValid()) return 'Please enter correct date';
                        return true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <DatePicker
                        {...field}
                        value={value}
                        format="MM/DD/YYYY"
                        inputRef={ref}
                        onChange={val => onChange(val)}
                        slotProps={{
                          textField: {
                            error: !!errors.report_due_date,
                            helperText: errors.report_due_date?.message,
                            size: 'small',
                            fullWidth: true,
                            InputProps: { sx: inputStyles },
                            variant: 'outlined',
                            disabled: isSubmitting
                          }
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
          </TableBody>
        </SectionTable>
      </Box>
    );
  }
);

Battery.displayName = 'Battery';

export default Battery;

import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import dayjs, { Dayjs } from 'dayjs';
import CustomParseFormatPlugin from 'dayjs/plugin/customParseFormat';
import { DatePicker } from '@mui/x-date-pickers';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import Table from '@mui/material/Table';
import TableRow from '@mui/material/TableRow';
import TableBody from '@mui/material/TableBody';
import FormHelperText from '@mui/material/FormHelperText';

import { FieldCell, TextBox } from '../../InformationCardBase/InformationCardBase.styles';
import {
  InformationCardFormProps,
  InformationCardFormRef,
  InformationCardBase
} from '../../InformationCardBase/InformationCardBase';
import { useNotify } from '../../../../../../../../../contexts/notifications/notifications';
import { ApiClient } from '../../../../../../../../../api';

dayjs.extend(CustomParseFormatPlugin);

type ComplianceCardData = Awaited<ReturnType<typeof ApiClient.assetManagement.siteInfo>>['compliance'];

interface ComplianceFormFields {
  entity: string | null;
  bank: string | null;
  report_due_date: Dayjs | null;
  fiscal_year_end: Dayjs | null;
  tax_return_deadline: Dayjs | null;
}

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

const ComplianceForm = React.forwardRef<InformationCardFormRef, InformationCardFormProps<ComplianceCardData>>(
  ({ mode, setMode, siteId, data, reflectFormState }, ref) => {
    const queryClient = useQueryClient();
    const notify = useNotify();

    const { handleSubmit, formState, control, reset } = useForm<ComplianceFormFields>({
      mode: 'onChange',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        entity: data.entity || null,
        bank: data.bank || null,
        report_due_date: data.report_due_date ? dayjs(data.report_due_date, 'YYYY-MM-DD', true) : null,
        fiscal_year_end: data.fiscal_year_end ? dayjs(data.fiscal_year_end, 'YYYY-MM-DD', true) : null,
        tax_return_deadline: data.tax_return_deadline ? dayjs(data.tax_return_deadline, 'YYYY-MM-DD', true) : null
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateComplianceDetails } = useMutation({
      mutationFn: (attributes: ComplianceFormFields) =>
        ApiClient.assetManagement.updateSiteInfo({
          siteId,
          section: 'compliance',
          data: {
            entity: attributes.entity || null,
            bank: attributes.bank || null,
            report_due_date: attributes.report_due_date ? attributes.report_due_date.format('YYYY-MM-DD') : null,
            fiscal_year_end: attributes.fiscal_year_end ? attributes.fiscal_year_end.format('YYYY-MM-DD') : null,
            tax_return_deadline: attributes.tax_return_deadline
              ? attributes.tax_return_deadline.format('YYYY-MM-DD')
              : null
          }
        })
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
        entity: data.entity || null,
        bank: data.bank || null,
        report_due_date: data.report_due_date ? dayjs(data.report_due_date, 'YYYY-MM-DD', true) : null,
        fiscal_year_end: data.fiscal_year_end ? dayjs(data.fiscal_year_end, 'YYYY-MM-DD', true) : null,
        tax_return_deadline: data.tax_return_deadline ? dayjs(data.tax_return_deadline, 'YYYY-MM-DD', true) : null
      });
    }, [data, reset]);

    const onSubmit: SubmitHandler<ComplianceFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateComplianceDetails(data);
          notify(response.message || `Compliance information was successfully updated.`);
          reset(data);
          queryClient.invalidateQueries({ queryKey: ['sites'] });
          setMode('view');
        } catch (e: any) {
          notify(e.response?.data?.message || 'Something went wrong when updating the Compliance information...');
        }
      },
      [notify, queryClient, reset, setMode, updateComplianceDetails]
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
        <Table sx={{ width: '100%', height: 'auto', tableLayout: 'fixed' }} size="small">
          <TableBody>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Compliance Entity:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.entity}</TextBox>
                ) : (
                  <Controller
                    name="entity"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Compliance Entity length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.entity}
                        multiline
                        required
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{ sx: inputStyles }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            {errors.entity?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.entity?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Compliance Bank:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.bank}</TextBox>
                ) : (
                  <Controller
                    name="bank"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Compliance Bank Type length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.bank}
                        multiline
                        required
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{ sx: inputStyles }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            {errors.bank?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.bank?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Report Due Date:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {data.report_due_date ? dayjs(data.report_due_date, 'YYYY-MM-DD', true).format('MM/DD/YYYY') : null}
                  </TextBox>
                ) : (
                  <Controller
                    name="report_due_date"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        return dayjs(value).isValid() || 'Please enter correct Report Due Date.';
                      }
                    }}
                    render={({ field: { ref, value, onChange, onBlur, ...field } }) => (
                      <DatePicker
                        {...field}
                        value={value}
                        format="MM/DD/YYYY"
                        inputRef={ref}
                        onChange={val => onChange(val)}
                        slotProps={{
                          textField: {
                            onBlur,
                            disabled: isSubmitting,
                            error: !!errors.report_due_date,
                            size: 'small',
                            fullWidth: true,
                            InputProps: { sx: inputStyles },
                            variant: 'outlined'
                          }
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            {errors.report_due_date?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.report_due_date?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Fiscal Year End:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {data.fiscal_year_end ? dayjs(data.fiscal_year_end, 'YYYY-MM-DD', true).format('MM/DD/YYYY') : null}
                  </TextBox>
                ) : (
                  <Controller
                    name="fiscal_year_end"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        return dayjs(value).isValid() || 'Please enter correct Fiscal Year End.';
                      }
                    }}
                    render={({ field: { ref, value, onChange, onBlur, ...field } }) => (
                      <DatePicker
                        {...field}
                        value={value}
                        format="MM/DD/YYYY"
                        inputRef={ref}
                        onChange={val => onChange(val)}
                        slotProps={{
                          textField: {
                            onBlur,
                            disabled: isSubmitting,
                            error: !!errors.fiscal_year_end,
                            size: 'small',
                            fullWidth: true,
                            InputProps: { sx: inputStyles },
                            variant: 'outlined'
                          }
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            {errors.fiscal_year_end?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.fiscal_year_end?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Tax Return Deadline:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {data.tax_return_deadline
                      ? dayjs(data.tax_return_deadline, 'YYYY-MM-DD', true).format('MM/DD/YYYY')
                      : null}
                  </TextBox>
                ) : (
                  <Controller
                    name="tax_return_deadline"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        return dayjs(value).isValid() || 'Please enter correct Tax Return Deadline.';
                      }
                    }}
                    render={({ field: { ref, value, onChange, onBlur, ...field } }) => (
                      <DatePicker
                        {...field}
                        value={value}
                        format="MM/DD/YYYY"
                        inputRef={ref}
                        onChange={val => onChange(val)}
                        slotProps={{
                          textField: {
                            onBlur,
                            disabled: isSubmitting,
                            error: !!errors.tax_return_deadline,
                            size: 'small',
                            fullWidth: true,
                            InputProps: { sx: inputStyles },
                            variant: 'outlined'
                          }
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            {errors.tax_return_deadline?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.tax_return_deadline?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Box>
    );
  }
);

ComplianceForm.displayName = 'ComplianceForm';

interface ComplianceCardProps {
  siteId: number;
  data: ComplianceCardData;
}

export const ComplianceCard: React.FC<ComplianceCardProps> = ({ siteId, data }) => (
  <InformationCardBase<ComplianceCardData>
    title="Compliance"
    informationCardData={data}
    siteId={siteId}
    InformationCardForm={ComplianceForm}
  />
);

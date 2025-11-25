import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import Table from '@mui/material/Table';
import TableRow from '@mui/material/TableRow';
import TableBody from '@mui/material/TableBody';
import dayjs, { Dayjs } from 'dayjs';
import { DatePicker } from '@mui/x-date-pickers';
import CustomParseFormatPlugin from 'dayjs/plugin/customParseFormat';
dayjs.extend(CustomParseFormatPlugin);

import { FieldCell, TextBox } from '../../InformationCardBase/InformationCardBase.styles';
import {
  InformationCardFormProps,
  InformationCardFormRef,
  InformationCardBase
} from '../../InformationCardBase/InformationCardBase';
import { useNotify } from '../../../../../../../../../contexts/notifications/notifications';

import { ApiClient } from '../../../../../../../../../api';
import formFloatValue from '../../../../../../../../../utils/formatters/formatFloatValue';
import FormHelperText from '@mui/material/FormHelperText';
import FormattedNumericInput from '../../../../../../../../../components/common/FormattedNumericInput/FormattedNumericInput';

type TaxEquityData = Exclude<Awaited<ReturnType<typeof ApiClient.assetManagement.siteInfo>>['tax_equity'], null>;

interface TaxEquityFormFields {
  tax_equity_fund: string | null;
  tax_equity_provider: string | null;
  tax_equity_buyout_amount: string | null;
  tax_equity_pref_rate: string | null;
  smartsheet_data_tape: string | null;
  tax_equity_buyout_date: Dayjs | null;
}

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

const TaxEquityForm = React.forwardRef<InformationCardFormRef, InformationCardFormProps<TaxEquityData>>(
  ({ mode, setMode, siteId, data, reflectFormState }, ref) => {
    const queryClient = useQueryClient();
    const notify = useNotify();

    const { handleSubmit, formState, control, reset } = useForm<TaxEquityFormFields>({
      mode: 'onChange',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        tax_equity_fund: data.tax_equity_fund,
        tax_equity_provider: data.tax_equity_provider,
        tax_equity_buyout_amount: data.tax_equity_buyout_amount?.toFixed(2) ?? null,
        tax_equity_buyout_date: data.tax_equity_buyout_date
          ? dayjs(data.tax_equity_buyout_date, 'YYYY-MM-DD', true)
          : null,
        tax_equity_pref_rate: data.tax_equity_pref_rate?.toFixed(2) ?? null,
        smartsheet_data_tape: data.smartsheet_data_tape
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateTaxEquityDetails } = useMutation({
      mutationFn: (attributes: TaxEquityFormFields) =>
        ApiClient.assetManagement.updateSiteInfo({
          siteId,
          section: 'tax_equity',
          data: {
            tax_equity_fund: attributes.tax_equity_fund || null,
            tax_equity_provider: attributes.tax_equity_provider || null,
            tax_equity_buyout_amount: attributes.tax_equity_buyout_amount
              ? Number.parseFloat(attributes.tax_equity_buyout_amount.replaceAll(',', ''))
              : null,
            tax_equity_buyout_date: attributes.tax_equity_buyout_date
              ? attributes.tax_equity_buyout_date.format('YYYY-MM-DD')
              : null,
            tax_equity_pref_rate: attributes.tax_equity_pref_rate
              ? Number.parseFloat(attributes.tax_equity_pref_rate.replaceAll(',', ''))
              : null,
            smartsheet_data_tape: attributes.smartsheet_data_tape || null
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
        tax_equity_fund: data.tax_equity_fund,
        tax_equity_provider: data.tax_equity_provider,
        tax_equity_buyout_amount: data.tax_equity_buyout_amount?.toFixed(2) ?? null,
        tax_equity_buyout_date: data.tax_equity_buyout_date
          ? dayjs(data.tax_equity_buyout_date, 'YYYY-MM-DD', true)
          : null,
        tax_equity_pref_rate: data.tax_equity_pref_rate?.toFixed(2) ?? null,
        smartsheet_data_tape: data.smartsheet_data_tape
      });
    }, [data, reset]);

    const onSubmit: SubmitHandler<TaxEquityFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateTaxEquityDetails(data);
          notify(response.message || `Tax equity information was successfully updated.`);
          reset({
            tax_equity_fund: data.tax_equity_fund,
            tax_equity_provider: data.tax_equity_provider,
            tax_equity_buyout_amount: data.tax_equity_buyout_amount,
            tax_equity_buyout_date: data.tax_equity_buyout_date ? data.tax_equity_buyout_date : null,
            tax_equity_pref_rate: data.tax_equity_pref_rate,
            smartsheet_data_tape: data.smartsheet_data_tape
          });
          await queryClient.invalidateQueries({ queryKey: ['sites'] });
          setMode('view');
        } catch (e: any) {
          notify(e.response?.data?.message || 'Something went wrong when updating the Tax Equity information...');
        }
      },
      [notify, queryClient, reset, setMode, updateTaxEquityDetails]
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
                <TextBox fieldName>Tax Equity Fund:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.tax_equity_fund}</TextBox>
                ) : (
                  <Controller
                    name="tax_equity_fund"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Tax Equity Fund length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.tax_equity_fund}
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
            {errors.tax_equity_fund?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.tax_equity_fund?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Tax Equity Provider:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.tax_equity_provider}</TextBox>
                ) : (
                  <Controller
                    name="tax_equity_provider"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Tax Equity Provider length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.tax_equity_provider}
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
            {errors.tax_equity_provider?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.tax_equity_provider?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Tax Equity Buyout Amount:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {typeof data.tax_equity_buyout_amount === 'number'
                      ? formFloatValue(data.tax_equity_buyout_amount)
                      : null}
                  </TextBox>
                ) : (
                  <Controller
                    name="tax_equity_buyout_amount"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        if ((value as unknown as string).length > 100)
                          return 'Tax Equity Buyout Amount length should not exceed 100 characters.';
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Tax Equity Buyout Amount'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.tax_equity_buyout_amount}
                        multiline
                        required
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{ inputComponent: FormattedNumericInput as any, ref: ref, sx: inputStyles }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            {errors.tax_equity_buyout_amount?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.tax_equity_buyout_amount?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Tax Equity Buyout Date:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {data.tax_equity_buyout_date
                      ? dayjs(data.tax_equity_buyout_date, 'YYYY-MM-DD', true).format('MM/DD/YYYY')
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="tax_equity_buyout_date"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        return dayjs(value).isValid() || 'Please enter correct Tax Equity Buyout Date.';
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
                            error: !!errors.tax_equity_buyout_date,
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
            {errors.tax_equity_buyout_date?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.tax_equity_buyout_date?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Tax Equity Pref Rate, %:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.tax_equity_pref_rate ? data.tax_equity_pref_rate : null}</TextBox>
                ) : (
                  <Controller
                    name="tax_equity_pref_rate"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Tax Equity Pref Rate'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.tax_equity_pref_rate}
                        multiline
                        required
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
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
            {errors.tax_equity_pref_rate?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.tax_equity_pref_rate?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Smartsheet Data Tape:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.smartsheet_data_tape}</TextBox>
                ) : (
                  <Controller
                    name="smartsheet_data_tape"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        if ((value as unknown as string).length > 100)
                          return 'Smartsheet Data Tape length should not exceed 100 characters.';
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Smartsheet Data Tape'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.smartsheet_data_tape}
                        multiline
                        required
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{ inputComponent: FormattedNumericInput as any, ref: ref, sx: inputStyles }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            {errors.smartsheet_data_tape?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.smartsheet_data_tape?.message}
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

TaxEquityForm.displayName = 'TaxEquityForm';

interface TaxEquityCardProps {
  siteId: number;
  data: TaxEquityData;
}

export const TaxEquityCard: React.FC<TaxEquityCardProps> = ({ siteId, data }) => (
  <InformationCardBase<TaxEquityData>
    title="Tax Equity"
    informationCardData={data}
    siteId={siteId}
    InformationCardForm={TaxEquityForm}
  />
);

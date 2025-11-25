import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import Table from '@mui/material/Table';
import TableRow from '@mui/material/TableRow';
import TableBody from '@mui/material/TableBody';
import FormHelperText from '@mui/material/FormHelperText';
import { Dayjs } from 'dayjs';

import { FieldCell, TextBox } from '../../InformationCardBase/InformationCardBase.styles';
import {
  InformationCardFormProps,
  InformationCardFormRef,
  InformationCardBase
} from '../../InformationCardBase/InformationCardBase';
import { useNotify } from '../../../../../../../../../contexts/notifications/notifications';
import { ApiClient } from '../../../../../../../../../api';
import FormattedIntegerNumericInput from '../../../../../../../../../components/common/FormattedIntegerNumericInput/FormattedIntegerNumericInput';
import formatPhoneNumber from '../../../../../../../../../utils/formatters/formatPhoneNumber';
import dayjs from 'dayjs';
import { DatePicker } from '@mui/x-date-pickers';
import CustomParseFormatPlugin from 'dayjs/plugin/customParseFormat';
import { StyledSelectItem } from '../../../../../../DeviceDetails/tabs/Overview/components/GeneralDeviceInfoCard/GeneralDeviceInfoCard.styles';
dayjs.extend(CustomParseFormatPlugin);

type SiteLeaseCardData = Awaited<ReturnType<typeof ApiClient.assetManagement.siteInfo>>['site_lease'];

type SiteLeaseFormFields = {
  rent_escalator?: string | null;
  payment_due_date?: Dayjs | null;
  lease_payment_method?: string | null;
  lease_payment_frequency?: string | null;
  landlord_contact_phone?: string | null;
  landlord: string | null;
  tenant: string | null;
  property_size: string | null;
  effective_date: string | null;
  rent_commencement: string | null;
  rent_amount: string | null;
  rent_escalator_effective_date: string | null;
  initial_term: string | null;
  renewal_terms: string | null;
};

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

const SiteLeaseForm = React.forwardRef<InformationCardFormRef, InformationCardFormProps<SiteLeaseCardData>>(
  ({ mode, setMode, siteId, data, reflectFormState }, ref) => {
    const queryClient = useQueryClient();
    const notify = useNotify();

    const { handleSubmit, formState, control, reset } = useForm<SiteLeaseFormFields>({
      mode: 'onChange',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        rent_escalator: data.rent_escalator || null,
        landlord_contact_phone: data.landlord_contact_phone || null,
        payment_due_date: data.payment_due_date ? dayjs(data.payment_due_date, 'YYYY-MM-DD', true) : null,
        lease_payment_frequency: data.lease_payment_frequency || null,
        lease_payment_method: data.lease_payment_method || null
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateSiteLeaseDetails } = useMutation({
      mutationFn: (attributes: SiteLeaseFormFields) =>
        ApiClient.assetManagement.updateSiteInfo({
          siteId,
          section: 'site_lease',
          data: {
            rent_escalator: attributes.rent_escalator || null,
            landlord_contact_phone: attributes.landlord_contact_phone || null,
            payment_due_date: attributes.payment_due_date ? attributes.payment_due_date.format('YYYY-MM-DD') : null,
            lease_payment_frequency: attributes.lease_payment_frequency || null,
            lease_payment_method: attributes.lease_payment_method || null
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
        rent_escalator: data.rent_escalator || null,
        landlord_contact_phone: data.landlord_contact_phone || null,
        payment_due_date: data.payment_due_date ? dayjs(data.payment_due_date, 'YYYY-MM-DD', true) : null,
        lease_payment_frequency: data.lease_payment_frequency || null,
        lease_payment_method: data.lease_payment_method || null
      });
    }, [data, reset]);

    const onSubmit: SubmitHandler<SiteLeaseFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateSiteLeaseDetails(data);
          notify(response.message || `Site Lease information was successfully updated.`);
          reset(data);
          queryClient.invalidateQueries({ queryKey: ['sites'] });
          setMode('view');
        } catch (e: any) {
          notify(e.response?.data?.message || 'Something went wrong when updating the Site Lease information...');
        }
      },
      [notify, queryClient, reset, setMode, updateSiteLeaseDetails]
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
                <TextBox fieldName>Landlord:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.landlord}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Tenant:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.tenant}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Property Size:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.property_size}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Effective Date:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.effective_date}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Rent Commencement:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.rent_commencement}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Rent Amount:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.rent_amount}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Rent Escalator (Amount):</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.rent_escalator}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Rent Escalator Effective Date:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.rent_escalator_effective_date}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Payment Due Date:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {data.payment_due_date
                      ? dayjs(data.payment_due_date, 'YYYY-MM-DD', true).format('MM/DD/YYYY')
                      : null}
                  </TextBox>
                ) : (
                  <Controller
                    name="payment_due_date"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        return dayjs(value).isValid() || 'Please enter correct Payment Due Date.';
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
                            error: !!errors.payment_due_date,
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
            {errors.payment_due_date?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.payment_due_date?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Lease Payment Method:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.lease_payment_method}</TextBox>
                ) : (
                  <Controller
                    name="lease_payment_method"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        placeholder=""
                        disabled={isSubmitting}
                        InputProps={{
                          sx: inputStyles
                        }}
                        select
                        fullWidth
                        variant="outlined"
                        size="small"
                      >
                        {['Check', 'Credit Card', 'Wire'].map(status => (
                          <StyledSelectItem key={status} value={status}>
                            {status}
                          </StyledSelectItem>
                        ))}
                      </TextField>
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            {errors.lease_payment_method?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.lease_payment_method?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Lease Payment Frequency:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.lease_payment_frequency}</TextBox>
                ) : (
                  <Controller
                    name="lease_payment_frequency"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        placeholder=""
                        disabled={isSubmitting}
                        InputProps={{
                          sx: inputStyles
                        }}
                        select
                        fullWidth
                        variant="outlined"
                        size="small"
                      >
                        {['Monthly', 'Quarterly', 'Semi Annual', 'Annual'].map(status => (
                          <StyledSelectItem key={status} value={status}>
                            {status}
                          </StyledSelectItem>
                        ))}
                      </TextField>
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            {errors.lease_payment_frequency?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.lease_payment_frequency?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Initial Term:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.initial_term}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Renewal Terms:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.renewal_terms}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Landlord Contact Phone #:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{formatPhoneNumber(data.landlord_contact_phone)}</TextBox>
                ) : (
                  <Controller
                    name="landlord_contact_phone"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        if (value.length > 10) return 'Contact Phone # length should not exceed 10 characters.';
                        return /^\d{10}$/.test(value) || 'Please provide correct Contact Phone.';
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.landlord_contact_phone}
                        multiline
                        required
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onInput={(e: React.ChangeEvent<HTMLInputElement>) => {
                          e.target.value = e.target.value.replace(/[^\d]/g, '').slice(0, 10);
                        }}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{ inputComponent: FormattedIntegerNumericInput as any, ref: ref, sx: inputStyles }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            {errors.landlord_contact_phone?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.landlord_contact_phone?.message}
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

SiteLeaseForm.displayName = 'SiteLeaseForm';

interface SiteLeaseCardProps {
  siteId: number;
  data: SiteLeaseCardData;
}

export const SiteLeaseCard: React.FC<SiteLeaseCardProps> = ({ siteId, data }) => (
  <InformationCardBase
    title="Site Lease"
    informationCardData={data}
    siteId={siteId}
    InformationCardForm={SiteLeaseForm}
  />
);

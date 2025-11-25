import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
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
import FormattedIntegerNumericInput from '../../../../../../../../../components/common/FormattedIntegerNumericInput/FormattedIntegerNumericInput';
import formatPhoneNumber from '../../../../../../../../../utils/formatters/formatPhoneNumber';
import FormattedNumericInput from '../../../../../../../../../components/common/FormattedNumericInput/FormattedNumericInput';
import formatFloatValue from '../../../../../../../../../utils/formatters/formatFloatValue';

type OMCardData = Awaited<ReturnType<typeof ApiClient.assetManagement.siteInfo>>['o_and_m'];

type OMFormFields = Pick<
  OMCardData,
  'om_address' | 'om_contact_name' | 'om_contact_email' | 'om_contact_phone' | 'o_and_m_rate'
>;

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

const OMForm = React.forwardRef<InformationCardFormRef, InformationCardFormProps<OMCardData>>(
  ({ mode, setMode, siteId, data, reflectFormState }, ref) => {
    const queryClient = useQueryClient();
    const notify = useNotify();

    const { handleSubmit, formState, control, reset } = useForm<OMFormFields>({
      mode: 'onChange',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        om_address: data.om_address || null,
        om_contact_email: data.om_contact_email || null,
        om_contact_name: data.om_contact_name || null,
        om_contact_phone: data.om_contact_phone || null,
        o_and_m_rate: data.o_and_m_rate || null
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateOMDetails } = useMutation({
      mutationFn: (attributes: OMFormFields) =>
        ApiClient.assetManagement.updateSiteInfo({
          siteId,
          section: 'o_and_m',
          data: {
            om_address: attributes.om_address || null,
            om_contact_name: attributes.om_contact_name || null,
            om_contact_email: attributes.om_contact_email || null,
            om_contact_phone: attributes.om_contact_phone || null,
            o_and_m_rate: attributes.o_and_m_rate || null
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
        om_address: data.om_address || null,
        om_contact_email: data.om_contact_email || null,
        om_contact_name: data.om_contact_name || null,
        om_contact_phone: data.om_contact_phone || null,
        o_and_m_rate: data.o_and_m_rate || null
      });
    }, [data, reset]);

    const onSubmit: SubmitHandler<OMFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateOMDetails(data);
          notify(response.message || `O&M information was successfully updated.`);
          reset({
            om_address: data.om_address,
            om_contact_email: data.om_contact_email,
            om_contact_name: data.om_contact_name,
            om_contact_phone: data.om_contact_phone
          });
          queryClient.invalidateQueries({ queryKey: ['sites'] });
          setMode('view');
        } catch (e: any) {
          notify(e.response?.data?.message || 'Something went wrong when updating the O&M information...');
        }
      },
      [notify, queryClient, reset, setMode, updateOMDetails]
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
                <TextBox fieldName>Provider:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.provider}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Address:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.om_address}</TextBox>
                ) : (
                  <Controller
                    name="om_address"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Address length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.om_address}
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
            {errors.om_address?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.om_address?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Contact Name:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.om_contact_name}</TextBox>
                ) : (
                  <Controller
                    name="om_contact_name"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Contact Name length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.om_contact_name}
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
            {errors.om_contact_name?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.om_contact_name?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Contact Email:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.om_contact_email}</TextBox>
                ) : (
                  <Controller
                    name="om_contact_email"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        if (value.length > 100) return 'Contact Email length should not exceed 100 characters.';
                        return (
                          /^(?!.*[.]{2})(?!.*\.@)(?!^[^a-zA-Z0-9]+$)(?![.-])[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+(?<![.])@(?=[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*(?:\.[a-zA-Z]{1,})+$)(?:[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*\.)+[a-zA-Z]{1,}$/.test(
                            value
                          ) || 'Please provide correct Contact Email.'
                        );
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        required
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.om_contact_email}
                        multiline
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
            {errors.om_contact_email?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.om_contact_email?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Contact Phone #:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{formatPhoneNumber(data.om_contact_phone)}</TextBox>
                ) : (
                  <Controller
                    name="om_contact_phone"
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
                        error={!!errors.om_contact_phone}
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
            {errors.om_contact_phone?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.om_contact_phone?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Agreement Effective Date:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.agreement_effective_date}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>O&M Rate:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.o_and_m_rate ? formatFloatValue(data.o_and_m_rate) : null}</TextBox>
                ) : (
                  <Controller
                    name="o_and_m_rate"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        if ((value as unknown as string).length > 100)
                          return 'O&M Rate length should not exceed 100 characters.';
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for O&M Rate'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.o_and_m_rate}
                        multiline
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
            {errors.o_and_m_rate?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.o_and_m_rate?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>O&M Escalator:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.o_and_m_escalator}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Production Guarantee:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.production_guarantee}</TextBox>
              </FieldCell>
            </TableRow>
          </TableBody>
        </Table>
      </Box>
    );
  }
);

OMForm.displayName = 'OMForm';

interface OMCardProps {
  siteId: number;
  data: OMCardData;
}

export const OMCard: React.FC<OMCardProps> = ({ siteId, data }) => (
  <InformationCardBase<OMCardData>
    title="O&M"
    informationCardData={data}
    siteId={siteId}
    InformationCardForm={OMForm}
  />
);

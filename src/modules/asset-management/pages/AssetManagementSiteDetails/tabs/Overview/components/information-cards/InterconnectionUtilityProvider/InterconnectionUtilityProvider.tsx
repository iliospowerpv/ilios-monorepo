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

type InterconnectionUtilityProviderCardData = Awaited<
  ReturnType<typeof ApiClient.assetManagement.siteInfo>
>['interconnection'];

type InterconnectionUtilityProviderFormFields = Pick<
  InterconnectionUtilityProviderCardData,
  'iut_address' | 'iut_contact_name' | 'iut_contact_email' | 'iut_contact_phone' | 'utility_rate'
>;

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

const InterconnectionUtilityProviderForm = React.forwardRef<
  InformationCardFormRef,
  InformationCardFormProps<InterconnectionUtilityProviderCardData>
>(({ mode, setMode, siteId, data, reflectFormState }, ref) => {
  const queryClient = useQueryClient();
  const notify = useNotify();

  const { handleSubmit, formState, control, reset } = useForm<InterconnectionUtilityProviderFormFields>({
    mode: 'onChange',
    criteriaMode: 'all',
    reValidateMode: 'onChange',
    defaultValues: {
      iut_address: data.iut_address || null,
      iut_contact_email: data.iut_contact_email || null,
      iut_contact_name: data.iut_contact_name || null,
      iut_contact_phone: data.iut_contact_phone || null,
      utility_rate: data.utility_rate || null
    }
  });

  const { errors, isValid, isSubmitting, isDirty } = formState;
  const { mutateAsync: updateInterconnectionUtilityProviderDetails } = useMutation({
    mutationFn: (attributes: InterconnectionUtilityProviderFormFields) =>
      ApiClient.assetManagement.updateSiteInfo({
        siteId,
        section: 'interconnection',
        data: {
          iut_address: attributes.iut_address || null,
          iut_contact_email: attributes.iut_contact_email || null,
          iut_contact_name: attributes.iut_contact_name || null,
          iut_contact_phone: attributes.iut_contact_phone || null,
          utility_rate: attributes.utility_rate || null
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
      iut_address: data.iut_address || null,
      iut_contact_email: data.iut_contact_email || null,
      iut_contact_name: data.iut_contact_name || null,
      iut_contact_phone: data.iut_contact_phone || null,
      utility_rate: data.utility_rate || null
    });
  }, [data, reset]);

  const onSubmit: SubmitHandler<InterconnectionUtilityProviderFormFields> = React.useCallback(
    async data => {
      try {
        const response = await updateInterconnectionUtilityProviderDetails(data);
        notify(response.message || `Interconnection Utility Provider information was successfully updated.`);
        reset(data);
        queryClient.invalidateQueries({ queryKey: ['sites'] });
        setMode('view');
      } catch (e: any) {
        notify(
          e.response?.data?.message ||
            'Something went wrong when updating the Interconnection Utility Provider information...'
        );
      }
    },
    [notify, queryClient, reset, setMode, updateInterconnectionUtilityProviderDetails]
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
                <TextBox>{data.iut_address}</TextBox>
              ) : (
                <Controller
                  name="iut_address"
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
                      error={!!errors.iut_address}
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
          {errors.iut_address?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.iut_address?.message}
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
                <TextBox>{data.iut_contact_name}</TextBox>
              ) : (
                <Controller
                  name="iut_contact_name"
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
                      error={!!errors.iut_contact_name}
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
          {errors.iut_contact_name?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.iut_contact_name?.message}
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
                <TextBox>{data.iut_contact_email}</TextBox>
              ) : (
                <Controller
                  name="iut_contact_email"
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
                      error={!!errors.iut_contact_email}
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
          {errors.iut_contact_email?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.iut_contact_email?.message}
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
                <TextBox>{formatPhoneNumber(data.iut_contact_phone)}</TextBox>
              ) : (
                <Controller
                  name="iut_contact_phone"
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
                      error={!!errors.iut_contact_phone}
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
          {errors.iut_contact_phone?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.iut_contact_phone?.message}
                  </FormHelperText>
                </TextBox>
              </FieldCell>
            </TableRow>
          )}
          <TableRow>
            <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
              <TextBox fieldName>PPA Effective Date:</TextBox>
            </FieldCell>
            <FieldCell component="th" scope="row" align="right">
              <TextBox>{data.ppa_effective_date}</TextBox>
            </FieldCell>
          </TableRow>
          <TableRow>
            <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
              <TextBox fieldName>PPA Term:</TextBox>
            </FieldCell>
            <FieldCell component="th" scope="row" align="right">
              <TextBox>{data.ppa_term}</TextBox>
            </FieldCell>
          </TableRow>
          <TableRow>
            <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
              <TextBox fieldName>Remaining PPA Term:</TextBox>
            </FieldCell>
            <FieldCell component="th" scope="row" align="right">
              <TextBox>{data.remaining_ppa_term}</TextBox>
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
          <TableRow>
            <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
              <TextBox fieldName>Interconnection Agreement Effective Date:</TextBox>
            </FieldCell>
            <FieldCell component="th" scope="row" align="right">
              <TextBox>{data.interconnection_agreement_effective_date}</TextBox>
            </FieldCell>
          </TableRow>
          <TableRow>
            <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
              <TextBox fieldName>Utility Rate:</TextBox>
            </FieldCell>
            <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
              {mode === 'view' ? (
                <TextBox>{data.utility_rate}</TextBox>
              ) : (
                <Controller
                  name="utility_rate"
                  control={control}
                  rules={{
                    maxLength: {
                      value: 100,
                      message: 'Utility Rate length should not exceed 100 characters.'
                    }
                  }}
                  render={({ field: { ref, value, onChange, ...field } }) => (
                    <TextField
                      {...field}
                      fullWidth
                      size="small"
                      placeholder=""
                      error={!!errors.utility_rate}
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
          {errors.utility_rate?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.utility_rate?.message}
                  </FormHelperText>
                </TextBox>
              </FieldCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </Box>
  );
});

InterconnectionUtilityProviderForm.displayName = 'InterconnectionUtilityProviderForm';

interface InterconnectionUtilityProviderCardProps {
  siteId: number;
  data: InterconnectionUtilityProviderCardData;
}

export const InterconnectionUtilityProviderCard: React.FC<InterconnectionUtilityProviderCardProps> = ({
  siteId,
  data
}) => (
  <InformationCardBase<InterconnectionUtilityProviderCardData>
    title="Interconnection Utility Provider"
    informationCardData={data}
    siteId={siteId}
    InformationCardForm={InterconnectionUtilityProviderForm}
  />
);

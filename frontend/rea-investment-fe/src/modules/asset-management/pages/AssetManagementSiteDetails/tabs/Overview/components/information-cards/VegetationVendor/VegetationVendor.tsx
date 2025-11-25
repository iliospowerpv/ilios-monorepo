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

type VegetationVendorCardData = Exclude<
  Awaited<ReturnType<typeof ApiClient.assetManagement.siteInfo>>['vegetation_vendor'],
  null
>;

type VegetationVendorFormFields = VegetationVendorCardData;

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

const VegetationVendorForm = React.forwardRef<
  InformationCardFormRef,
  InformationCardFormProps<VegetationVendorFormFields>
>(({ mode, setMode, siteId, data, reflectFormState }, ref) => {
  const queryClient = useQueryClient();
  const notify = useNotify();

  const { handleSubmit, formState, control, reset } = useForm<VegetationVendorFormFields>({
    mode: 'onChange',
    criteriaMode: 'all',
    reValidateMode: 'onChange',
    defaultValues: {
      vv_provider: data.vv_provider || null,
      vv_address: data.vv_address || null,
      vv_contact_name: data.vv_contact_name || null,
      vv_contact_email: data.vv_contact_email || null,
      vv_contact_phone: data.vv_contact_phone || null
    }
  });

  const { errors, isValid, isSubmitting, isDirty } = formState;
  const { mutateAsync: updateVegetationVendorDetails } = useMutation({
    mutationFn: (attributes: VegetationVendorFormFields) =>
      ApiClient.assetManagement.updateSiteInfo({
        siteId,
        section: 'vegetation_vendor',
        data: {
          vv_provider: attributes.vv_provider || null,
          vv_address: attributes.vv_address || null,
          vv_contact_name: attributes.vv_contact_name || null,
          vv_contact_email: attributes.vv_contact_email || null,
          vv_contact_phone: attributes.vv_contact_phone || null
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
      vv_provider: data.vv_provider || null,
      vv_address: data.vv_address || null,
      vv_contact_name: data.vv_contact_name || null,
      vv_contact_email: data.vv_contact_email || null,
      vv_contact_phone: data.vv_contact_phone || null
    });
  }, [data, reset]);

  const onSubmit: SubmitHandler<VegetationVendorFormFields> = React.useCallback(
    async data => {
      try {
        const response = await updateVegetationVendorDetails(data);
        notify(response.message || `Vegetation Vendor information was successfully updated.`);
        reset(data);
        queryClient.invalidateQueries({ queryKey: ['sites'] });
        setMode('view');
      } catch (e: any) {
        notify(e.response?.data?.message || 'Something went wrong when updating the Vegetation Vendor information...');
      }
    },
    [notify, queryClient, reset, setMode, updateVegetationVendorDetails]
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
            <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
              {mode === 'view' ? (
                <TextBox>{data.vv_provider}</TextBox>
              ) : (
                <Controller
                  name="vv_provider"
                  control={control}
                  rules={{
                    maxLength: {
                      value: 100,
                      message: 'Provider length should not exceed 100 characters.'
                    }
                  }}
                  render={({ field: { ref, value, onChange, ...field } }) => (
                    <TextField
                      {...field}
                      fullWidth
                      size="small"
                      placeholder=""
                      error={!!errors.vv_provider}
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
          {errors.vv_provider?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.vv_provider?.message}
                  </FormHelperText>
                </TextBox>
              </FieldCell>
            </TableRow>
          )}
          <TableRow>
            <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
              <TextBox fieldName>Address:</TextBox>
            </FieldCell>
            <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
              {mode === 'view' ? (
                <TextBox>{data.vv_address}</TextBox>
              ) : (
                <Controller
                  name="vv_address"
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
                      error={!!errors.vv_address}
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
          {errors.vv_address?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.vv_address?.message}
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
                <TextBox>{data.vv_contact_name}</TextBox>
              ) : (
                <Controller
                  name="vv_contact_name"
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
                      error={!!errors.vv_contact_name}
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
          {errors.vv_contact_name?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.vv_contact_name?.message}
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
                <TextBox>{data.vv_contact_email}</TextBox>
              ) : (
                <Controller
                  name="vv_contact_email"
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
                      error={!!errors.vv_contact_email}
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
          {errors.vv_contact_email?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.vv_contact_email?.message}
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
                <TextBox>{formatPhoneNumber(data.vv_contact_phone)}</TextBox>
              ) : (
                <Controller
                  name="vv_contact_phone"
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
                      error={!!errors.vv_contact_phone}
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
          {errors.vv_contact_phone?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.vv_contact_phone?.message}
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

VegetationVendorForm.displayName = 'VegetationVendorForm';

interface VegetationVendorCardProps {
  siteId: number;
  data: VegetationVendorCardData;
}

export const VegetationVendorCard: React.FC<VegetationVendorCardProps> = ({ siteId, data }) => (
  <InformationCardBase<VegetationVendorCardData>
    title="Vegetation Vendor"
    informationCardData={data}
    siteId={siteId}
    InformationCardForm={VegetationVendorForm}
  />
);

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
import FormHelperText from '@mui/material/FormHelperText';
import formatPhoneNumber from '../../../../../../../../../utils/formatters/formatPhoneNumber';
import FormattedIntegerNumericInput from '../../../../../../../../../components/common/FormattedIntegerNumericInput/FormattedIntegerNumericInput';
import FormattedNumericInput from '../../../../../../../../../components/common/FormattedNumericInput/FormattedNumericInput';

type CommunitySolarManagerData = Exclude<
  Awaited<ReturnType<typeof ApiClient.assetManagement.siteInfo>>['community_solar_manager'],
  null
>;

interface CommunitySolarManagerFormFields {
  csm_provider: string | null;
  csm_address: string | null;
  csm_contact_name: string | null;
  csm_contact_email: string | null;
  csm_contact_phone: string | null;
  csm_fee: string | null;
  escalator: string | null;
  escalator_effective: Dayjs | null;
}

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

const CommunitySolarManagerForm = React.forwardRef<
  InformationCardFormRef,
  InformationCardFormProps<CommunitySolarManagerData>
>(({ mode, setMode, siteId, data, reflectFormState }, ref) => {
  const queryClient = useQueryClient();
  const notify = useNotify();

  const { handleSubmit, formState, control, reset } = useForm<CommunitySolarManagerFormFields>({
    mode: 'onChange',
    criteriaMode: 'all',
    reValidateMode: 'onChange',
    defaultValues: {
      csm_provider: data.csm_provider,
      csm_address: data.csm_address,
      csm_contact_name: data.csm_contact_name,
      csm_contact_email: data.csm_contact_email,
      csm_contact_phone: data.csm_contact_phone,
      csm_fee: data.csm_fee?.toFixed(2),
      escalator: data.escalator?.toFixed(2),
      escalator_effective: data.escalator_effective ? dayjs(data.escalator_effective, 'YYYY-MM-DD', true) : null
    }
  });

  const { errors, isValid, isSubmitting, isDirty } = formState;
  const { mutateAsync: updateCommunitySolarManagerDetails } = useMutation({
    mutationFn: (attributes: CommunitySolarManagerFormFields) =>
      ApiClient.assetManagement.updateSiteInfo({
        siteId,
        section: 'community_solar_manager',
        data: {
          csm_provider: attributes.csm_provider || null,
          csm_address: attributes.csm_address || null,
          csm_contact_name: attributes.csm_contact_name || null,
          csm_contact_phone: attributes.csm_contact_phone || null,
          escalator_effective: attributes.escalator_effective
            ? attributes.escalator_effective.format('YYYY-MM-DD')
            : null,
          csm_contact_email: attributes.csm_contact_email || null,
          csm_fee: attributes.csm_fee ? Number.parseFloat(attributes.csm_fee.replaceAll(',', '')) : null,
          escalator: attributes.escalator ? Number.parseFloat(attributes.escalator.replaceAll(',', '')) : null
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
      csm_provider: data.csm_provider,
      csm_address: data.csm_address,
      csm_contact_name: data.csm_contact_name,
      csm_contact_email: data.csm_contact_email,
      csm_contact_phone: data.csm_contact_phone,
      csm_fee: data.csm_fee?.toFixed(2),
      escalator: data.escalator?.toFixed(2),
      escalator_effective: data.escalator_effective ? dayjs(data.escalator_effective, 'YYYY-MM-DD', true) : null
    });
  }, [data, reset]);

  const onSubmit: SubmitHandler<CommunitySolarManagerFormFields> = React.useCallback(
    async data => {
      try {
        const response = await updateCommunitySolarManagerDetails(data);
        notify(response.message || `Community Solar Manager information was successfully updated.`);
        reset({
          csm_provider: data.csm_provider,
          csm_address: data.csm_address,
          csm_contact_name: data.csm_contact_name,
          csm_contact_email: data.csm_contact_email,
          csm_contact_phone: data.csm_contact_phone,
          csm_fee: data.csm_fee,
          escalator: data.escalator,
          escalator_effective: data.escalator_effective
        });
        await queryClient.invalidateQueries({ queryKey: ['sites'] });
        setMode('view');
      } catch (e: any) {
        notify(
          e.response?.data?.message || 'Something went wrong when updating the Community Solar Manager information...'
        );
      }
    },
    [notify, queryClient, reset, setMode, updateCommunitySolarManagerDetails]
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
                <TextBox>{data.csm_provider}</TextBox>
              ) : (
                <Controller
                  name="csm_provider"
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
                      error={!!errors.csm_provider}
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
          {errors.csm_provider?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.csm_provider?.message}
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
                <TextBox>{data.csm_address}</TextBox>
              ) : (
                <Controller
                  name="csm_address"
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
                      error={!!errors.csm_address}
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
          {errors.csm_address?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.csm_address?.message}
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
                <TextBox>{data.csm_contact_name}</TextBox>
              ) : (
                <Controller
                  name="csm_contact_name"
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
                      error={!!errors.csm_contact_name}
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
          {errors.csm_contact_name?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.csm_contact_name?.message}
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
                <TextBox>{data.csm_contact_email}</TextBox>
              ) : (
                <Controller
                  name="csm_contact_email"
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
                      fullWidth
                      size="small"
                      placeholder=""
                      error={!!errors.csm_contact_email}
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
          {errors.csm_contact_email?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.csm_contact_email?.message}
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
                <TextBox>{formatPhoneNumber(data.csm_contact_phone)}</TextBox>
              ) : (
                <Controller
                  name="csm_contact_phone"
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
                      error={!!errors.csm_contact_phone}
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
          {errors.csm_contact_phone?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.csm_contact_phone?.message}
                  </FormHelperText>
                </TextBox>
              </FieldCell>
            </TableRow>
          )}
          <TableRow>
            <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
              <TextBox fieldName>Community Solar Management Fee, %:</TextBox>
            </FieldCell>
            <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
              {mode === 'view' ? (
                <TextBox>{data.csm_fee ? data.csm_fee : null}</TextBox>
              ) : (
                <Controller
                  name="csm_fee"
                  control={control}
                  rules={{
                    validate: value => {
                      if (!value) return true;
                      if ((value as unknown as string).length > 100)
                        return 'Community Solar Management Fee length should not exceed 100 characters.';
                      const withoutThousandSeparators = value.toString().replaceAll(',', '');
                      return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                        ? 'Invalid number provided as a value for Community Solar Management Fee'
                        : true;
                    }
                  }}
                  render={({ field: { ref, value, onChange, ...field } }) => (
                    <TextField
                      {...field}
                      fullWidth
                      size="small"
                      placeholder=""
                      error={!!errors.csm_fee}
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
          {errors.csm_fee?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.csm_fee?.message}
                  </FormHelperText>
                </TextBox>
              </FieldCell>
            </TableRow>
          )}
          <TableRow>
            <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
              <TextBox fieldName>Escalator, $:</TextBox>
            </FieldCell>
            <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
              {mode === 'view' ? (
                <TextBox>{data.escalator ? data.escalator : null}</TextBox>
              ) : (
                <Controller
                  name="escalator"
                  control={control}
                  rules={{
                    validate: value => {
                      if (!value) return true;
                      if ((value as unknown as string).length > 100)
                        return 'Escalator length should not exceed 100 characters.';
                      const withoutThousandSeparators = value.toString().replaceAll(',', '');
                      return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                        ? 'Invalid number provided as a value for Escalator'
                        : true;
                    }
                  }}
                  render={({ field: { ref, value, onChange, ...field } }) => (
                    <TextField
                      {...field}
                      fullWidth
                      size="small"
                      placeholder=""
                      error={!!errors.escalator}
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
          {errors.escalator?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.escalator?.message}
                  </FormHelperText>
                </TextBox>
              </FieldCell>
            </TableRow>
          )}
          <TableRow>
            <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
              <TextBox fieldName>Escalator Effective:</TextBox>
            </FieldCell>
            <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
              {mode === 'view' ? (
                <TextBox>
                  {data.escalator_effective
                    ? dayjs(data.escalator_effective, 'YYYY-MM-DD', true).format('MM/DD/YYYY')
                    : ''}
                </TextBox>
              ) : (
                <Controller
                  name="escalator_effective"
                  control={control}
                  rules={{
                    validate: value => {
                      if (!value) return true;
                      return dayjs(value).isValid() || 'Please enter correct Escalator Effective.';
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
                          error: !!errors.escalator_effective,
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
          {errors.escalator_effective?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.escalator_effective?.message}
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

CommunitySolarManagerForm.displayName = 'CommunitySolarManagerForm';

interface CommunitySolarManagerCardProps {
  siteId: number;
  data: CommunitySolarManagerData;
}

export const CommunitySolarManagerCard: React.FC<CommunitySolarManagerCardProps> = ({ siteId, data }) => (
  <InformationCardBase<CommunitySolarManagerData>
    title="Community Solar Manager"
    informationCardData={data}
    siteId={siteId}
    InformationCardForm={CommunitySolarManagerForm}
  />
);

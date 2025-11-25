import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import TableRow from '@mui/material/TableRow';
import TableBody from '@mui/material/TableBody';

import { FieldCell, TextBox, SectionTable } from '../../TechnicalDetail.styles';
import { DeviceTechnicalDetailsFormProps, DeviceTechnicalDetailsFormRef } from '../../TechnicalDetailCard';
import formatFloatValue from '../../../../../../../../../../utils/formatters/formatFloatValue';
import {
  ApiClient,
  NetworkConnectionDeviceTechnicalDetails,
  TechnicalDetailAttributes
} from '../../../../../../../../../../api';
import { useNotify } from '../../../../../../../../../../contexts/notifications/notifications';

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

interface NetworkConnectionFormFields {
  account_number: string | null;
  provider: string | null;
}

const NetworkConnection = React.forwardRef<DeviceTechnicalDetailsFormRef, DeviceTechnicalDetailsFormProps>(
  ({ mode, category, setMode, siteId, deviceId, technicalDetailsData: technicalDetailData, reflectFormState }, ref) => {
    const queryClient = useQueryClient();
    const notify = useNotify();

    const { handleSubmit, formState, control, reset } = useForm<NetworkConnectionFormFields>({
      mode: 'onChange',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        account_number:
          typeof technicalDetailData.account_number === 'number'
            ? formatFloatValue(technicalDetailData.account_number, true)
            : technicalDetailData.account_number,
        provider:
          typeof technicalDetailData.provider === 'number'
            ? formatFloatValue(technicalDetailData.provider, true)
            : technicalDetailData.provider
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateDeviceTechnicalDetails } = useMutation({
      mutationFn: (attributes: NetworkConnectionDeviceTechnicalDetails) => {
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
        account_number:
          typeof technicalDetailData.account_number === 'number'
            ? formatFloatValue(technicalDetailData.account_number, true)
            : technicalDetailData.account_number,
        provider:
          typeof technicalDetailData.provider === 'number'
            ? formatFloatValue(technicalDetailData.provider, true)
            : technicalDetailData.provider
      });
    }, [technicalDetailData, reset]);

    const onSubmit: SubmitHandler<NetworkConnectionFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateDeviceTechnicalDetails({
            account_number: data.account_number ?? null,
            provider: data.provider ?? null
          });
          notify(response.message || `Technical details was successfully updated.`);
          reset({
            account_number: data.account_number,
            provider: data.provider
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
                <TextBox fieldName>Provider</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{technicalDetailData.provider || ''}</TextBox>
                ) : (
                  <Controller
                    name="provider"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Provider length should be less than 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.provider}
                        helperText={errors.provider?.message}
                        multiline
                        minRows={1}
                        maxRows={3}
                        inputRef={ref}
                        disabled={isSubmitting}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
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
                <TextBox fieldName>Account #</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{technicalDetailData.account_number || ''}</TextBox>
                ) : (
                  <Controller
                    name="account_number"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Account length should be less than 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.account_number}
                        helperText={errors.account_number?.message}
                        multiline
                        minRows={1}
                        maxRows={3}
                        inputRef={ref}
                        disabled={isSubmitting}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          sx: inputStyles
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

NetworkConnection.displayName = 'NetworkConnection';

export default NetworkConnection;

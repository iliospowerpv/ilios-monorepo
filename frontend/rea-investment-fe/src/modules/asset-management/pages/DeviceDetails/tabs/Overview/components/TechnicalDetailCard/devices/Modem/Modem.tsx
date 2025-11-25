import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import TableRow from '@mui/material/TableRow';
import TableBody from '@mui/material/TableBody';

import FormattedIntegerNumericInput from '../../../../../../../../../../components/common/FormattedIntegerNumericInput/FormattedIntegerNumericInput';
import { FieldCell, TextBox, SectionTitle, SectionTable } from '../../TechnicalDetail.styles';
import { DeviceTechnicalDetailsFormProps, DeviceTechnicalDetailsFormRef } from '../../TechnicalDetailCard';
import {
  ApiClient,
  ModemDeviceTechnicalDetails,
  ModemFormFields,
  TechnicalDetailAttributes
} from '../../../../../../../../../../api';
import { useNotify } from '../../../../../../../../../../contexts/notifications/notifications';

const intFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
  useGrouping: false
});
const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

const Modem = React.forwardRef<DeviceTechnicalDetailsFormRef, DeviceTechnicalDetailsFormProps>(
  ({ mode, category, setMode, siteId, deviceId, technicalDetailsData: technicalDetailData, reflectFormState }, ref) => {
    const queryClient = useQueryClient();
    const notify = useNotify();

    const { handleSubmit, formState, control, reset } = useForm<ModemFormFields>({
      mode: 'onChange',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        ip_address: technicalDetailData.communication.ip_address,
        port:
          technicalDetailData.communication.port !== null
            ? intFormatter.format(technicalDetailData.communication.port)
            : technicalDetailData.communication.port,
        serial_mode: technicalDetailData.communication.serial_mode,
        baud:
          technicalDetailData.communication.baud !== null
            ? intFormatter.format(technicalDetailData.communication.baud)
            : technicalDetailData.communication.baud
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateDeviceTechnicalDetails } = useMutation({
      mutationFn: (attributes: ModemDeviceTechnicalDetails) => {
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
        ip_address: technicalDetailData.communication.ip_address,
        port:
          technicalDetailData.communication.port !== null
            ? intFormatter.format(technicalDetailData.communication.port)
            : technicalDetailData.communication.port,
        serial_mode: technicalDetailData.communication.serial_mode,
        baud:
          technicalDetailData.communication.baud !== null
            ? intFormatter.format(technicalDetailData.communication.baud)
            : technicalDetailData.communication.baud
      });
    }, [technicalDetailData, reset]);

    const onSubmit: SubmitHandler<ModemFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateDeviceTechnicalDetails({
            communication: {
              ip_address: data.ip_address ?? null,
              port: data.port !== null ? Number.parseInt(data.port) : null,
              serial_mode: data.serial_mode ?? null,
              baud: data.baud !== null ? Number.parseInt(data.baud) : null
            }
          });
          notify(response.message || `Technical details was successfully updated.`);
          reset({
            ip_address: data.ip_address,
            port: data.port,
            serial_mode: data.serial_mode,
            baud: data.baud
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
        <SectionTitle variant="h6">Communication</SectionTitle>
        <SectionTable size="small">
          <TableBody>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>IP Address</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{technicalDetailData.communication.ip_address || ''}</TextBox>
                ) : (
                  <Controller
                    name="ip_address"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const pattern =
                          /^(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])){3}$/;
                        if (!pattern.test(value)) {
                          return 'Invalid IP address format. Example of a correct address: 192.168.0.1';
                        }
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.ip_address}
                        helperText={errors.ip_address?.message}
                        disabled={isSubmitting}
                        inputRef={ref}
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
                <TextBox fieldName>Port</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.communication.port !== null
                      ? intFormatter.format(technicalDetailData.communication.port)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="port"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        return Number.isNaN(Number.parseInt(value))
                          ? 'Invalid number provided as a value for Port'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.port}
                        helperText={errors.port?.message}
                        disabled={isSubmitting}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          inputComponent: FormattedIntegerNumericInput as any,
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
                <TextBox fieldName>Serial Mode</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{technicalDetailData.communication.serial_mode || ''}</TextBox>
                ) : (
                  <Controller
                    name="serial_mode"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Serial Mode length should be less than 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.serial_mode}
                        helperText={errors.serial_mode?.message}
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
                <TextBox fieldName>Baud</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.communication.baud !== null
                      ? intFormatter.format(technicalDetailData.communication.baud)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="baud"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        return Number.isNaN(Number.parseInt(value))
                          ? 'Invalid number provided as a value for Baud'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.baud}
                        helperText={errors.baud?.message}
                        disabled={isSubmitting}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          inputComponent: FormattedIntegerNumericInput as any,
                          ref: ref,
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

Modem.displayName = 'Modem';

export default Modem;

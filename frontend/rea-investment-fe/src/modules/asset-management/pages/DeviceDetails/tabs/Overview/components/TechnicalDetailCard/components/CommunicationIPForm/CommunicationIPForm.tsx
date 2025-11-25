import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import TableRow from '@mui/material/TableRow';
import TableBody from '@mui/material/TableBody';

import { FieldCell, TextBox, SectionTitle, SectionTable } from '../../TechnicalDetail.styles';
import { DeviceTechnicalDetailsFormProps, DeviceTechnicalDetailsFormRef } from '../../TechnicalDetailCard';
import {
  ApiClient,
  CameraDeviceTechnicalDetails,
  CameraFormFields,
  TechnicalDetailAttributes
} from '../../../../../../../../../../api';
import { useNotify } from '../../../../../../../../../../contexts/notifications/notifications';
const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

const CommunicationIPForm = React.forwardRef<DeviceTechnicalDetailsFormRef, DeviceTechnicalDetailsFormProps>(
  ({ mode, category, setMode, siteId, deviceId, technicalDetailsData: technicalDetailData, reflectFormState }, ref) => {
    const queryClient = useQueryClient();
    const notify = useNotify();

    const { handleSubmit, formState, control, reset } = useForm<CameraFormFields>({
      mode: 'onChange',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        ip_address: technicalDetailData.communication.ip_address
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateDeviceTechnicalDetails } = useMutation({
      mutationFn: (attributes: CameraDeviceTechnicalDetails) => {
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
        ip_address: technicalDetailData.communication.ip_address
      });
    }, [technicalDetailData, reset]);

    const onSubmit: SubmitHandler<CameraFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateDeviceTechnicalDetails({
            communication: {
              ip_address: data.ip_address ?? null
            }
          });
          notify(response.message || `Technical details was successfully updated.`);
          reset({
            ip_address: data.ip_address
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

    if (!category) {
      return null;
    }

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
          </TableBody>
        </SectionTable>
      </Box>
    );
  }
);

CommunicationIPForm.displayName = 'CommunicationIPForm';

export default CommunicationIPForm;

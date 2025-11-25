import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import TableRow from '@mui/material/TableRow';
import TableBody from '@mui/material/TableBody';

import FormattedNumericInput from '../../../../../../../../../../components/common/FormattedNumericInput/FormattedNumericInput';
import { FieldCell, TextBox, SectionTitle, SectionTable, StyledSelectItem } from '../../TechnicalDetail.styles';
import { DeviceTechnicalDetailsFormProps, DeviceTechnicalDetailsFormRef } from '../../TechnicalDetailCard';
import formatFloatValue from '../../../../../../../../../../utils/formatters/formatFloatValue';
import {
  ApiClient,
  RackMountDeviceTechnicalDetails,
  RackMountFormFields,
  TechnicalDetailAttributes
} from '../../../../../../../../../../api';
import { useNotify } from '../../../../../../../../../../contexts/notifications/notifications';

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

const RackMount = React.forwardRef<DeviceTechnicalDetailsFormRef, DeviceTechnicalDetailsFormProps>(
  ({ mode, category, setMode, siteId, deviceId, technicalDetailsData: technicalDetailData, reflectFormState }, ref) => {
    const queryClient = useQueryClient();
    const notify = useNotify();

    const { handleSubmit, formState, control, reset } = useForm<RackMountFormFields>({
      mode: 'onChange',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        azimuth: technicalDetailData.general.azimuth,
        racking_capacity: technicalDetailData.general.racking_capacity,
        tracking: technicalDetailData.general.tracking
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateDeviceTechnicalDetails } = useMutation({
      mutationFn: (attributes: RackMountDeviceTechnicalDetails) => {
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
        azimuth: technicalDetailData.general.azimuth,
        racking_capacity: technicalDetailData.general.racking_capacity,
        tracking: technicalDetailData.general.tracking
      });
    }, [technicalDetailData, reset]);

    const onSubmit: SubmitHandler<RackMountFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateDeviceTechnicalDetails({
            general: {
              azimuth: data.azimuth ?? null,
              racking_capacity: data.racking_capacity ?? null,
              tracking: data.tracking ?? null
            }
          });
          notify(response.message || `Technical details was successfully updated.`);
          reset({
            azimuth: data.azimuth,
            racking_capacity: data.racking_capacity,
            tracking: data.tracking
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
        <SectionTitle variant="h6">General</SectionTitle>
        <SectionTable size="small">
          <TableBody>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Racking Capacity (kWp DC)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.general.racking_capacity !== null
                      ? formatFloatValue(technicalDetailData.general.racking_capacity)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="racking_capacity"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Racking Capacity'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.racking_capacity}
                        helperText={errors.racking_capacity?.message}
                        disabled={isSubmitting}
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
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Azimuth (Degrees)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.general.azimuth !== null
                      ? formatFloatValue(technicalDetailData.general.azimuth)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="azimuth"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Azimuth'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.azimuth}
                        helperText={errors.azimuth?.message}
                        disabled={isSubmitting}
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
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Tracking</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{technicalDetailData.general.tracking || ''}</TextBox>
                ) : (
                  <Controller
                    name="tracking"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.tracking}
                        helperText={errors.tracking?.message}
                        InputProps={{
                          sx: inputStyles
                        }}
                        select
                        fullWidth
                        variant="outlined"
                        size="small"
                      >
                        <StyledSelectItem value="Yes">Yes</StyledSelectItem>
                        <StyledSelectItem value="No">No</StyledSelectItem>
                      </TextField>
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

RackMount.displayName = 'RackMount';

export default RackMount;

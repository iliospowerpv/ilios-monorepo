import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import TableRow from '@mui/material/TableRow';
import TableBody from '@mui/material/TableBody';

import FormattedNumericInput from '../../../../../../../../../../components/common/FormattedNumericInput/FormattedNumericInput';
import { FieldCell, TextBox, SectionTable } from '../../TechnicalDetail.styles';
import { DeviceTechnicalDetailsFormProps, DeviceTechnicalDetailsFormRef } from '../../TechnicalDetailCard';
import formatFloatValue from '../../../../../../../../../../utils/formatters/formatFloatValue';
import {
  ApiClient,
  TransformerDeviceTechnicalDetails,
  TechnicalDetailAttributes
} from '../../../../../../../../../../api';
import { useNotify } from '../../../../../../../../../../contexts/notifications/notifications';

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

interface TransformerFormFields {
  frequency: string | null;
  phase: string | null;
  rating: string | null;
  type: string | null;
  voltage: string | null;
  volts: string | null;
}

const Transformer = React.forwardRef<DeviceTechnicalDetailsFormRef, DeviceTechnicalDetailsFormProps>(
  ({ mode, category, setMode, siteId, deviceId, technicalDetailsData: technicalDetailData, reflectFormState }, ref) => {
    const queryClient = useQueryClient();
    const notify = useNotify();

    const { handleSubmit, formState, control, reset } = useForm<TransformerFormFields>({
      mode: 'onChange',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        frequency:
          typeof technicalDetailData.frequency === 'number'
            ? formatFloatValue(technicalDetailData.frequency, true)
            : technicalDetailData.frequency,
        phase:
          typeof technicalDetailData.phase === 'number'
            ? formatFloatValue(technicalDetailData.phase, true)
            : technicalDetailData.phase,
        rating:
          typeof technicalDetailData.rating === 'number'
            ? formatFloatValue(technicalDetailData.rating, true)
            : technicalDetailData.rating,
        type:
          typeof technicalDetailData.type === 'number'
            ? formatFloatValue(technicalDetailData.type, true)
            : technicalDetailData.type,
        voltage:
          typeof technicalDetailData.voltage === 'number'
            ? formatFloatValue(technicalDetailData.voltage, true)
            : technicalDetailData.voltage,
        volts:
          typeof technicalDetailData.volts === 'number'
            ? formatFloatValue(technicalDetailData.volts, true)
            : technicalDetailData.volts
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateDeviceTechnicalDetails } = useMutation({
      mutationFn: (attributes: TransformerDeviceTechnicalDetails) => {
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
        frequency:
          typeof technicalDetailData.frequency === 'number'
            ? formatFloatValue(technicalDetailData.frequency, true)
            : technicalDetailData.frequency,
        phase:
          typeof technicalDetailData.phase === 'number'
            ? formatFloatValue(technicalDetailData.phase, true)
            : technicalDetailData.phase,
        rating:
          typeof technicalDetailData.rating === 'number'
            ? formatFloatValue(technicalDetailData.rating, true)
            : technicalDetailData.rating,
        type:
          typeof technicalDetailData.type === 'number'
            ? formatFloatValue(technicalDetailData.type, true)
            : technicalDetailData.type,
        voltage:
          typeof technicalDetailData.voltage === 'number'
            ? formatFloatValue(technicalDetailData.voltage, true)
            : technicalDetailData.voltage,
        volts:
          typeof technicalDetailData.volts === 'number'
            ? formatFloatValue(technicalDetailData.volts, true)
            : technicalDetailData.volts
      });
    }, [technicalDetailData, reset]);

    const onSubmit: SubmitHandler<TransformerFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateDeviceTechnicalDetails({
            frequency: data.frequency ?? null,
            phase: data.phase ?? null,
            rating: data.rating ?? null,
            type: data.type ?? null,
            voltage: data.voltage ? Number.parseFloat(data.voltage.replaceAll(',', '')) : null,
            volts: data.volts ? Number.parseFloat(data.volts.replaceAll(',', '')) : null
          });
          notify(response.message || `Technical details was successfully updated.`);
          reset({
            frequency: data.frequency,
            phase: data.phase,
            rating: data.rating,
            type: data.type,
            voltage: data.voltage,
            volts: data.volts
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
                <TextBox fieldName>Type</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{technicalDetailData.type || ''}</TextBox>
                ) : (
                  <Controller
                    name="type"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Type length should be less than 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.type}
                        helperText={errors.type?.message}
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
                <TextBox fieldName>Rating (kVA)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{technicalDetailData.rating || ''}</TextBox>
                ) : (
                  <Controller
                    name="rating"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Rating length should be less than 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.rating}
                        helperText={errors.rating?.message}
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
                <TextBox fieldName>Frequency</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{technicalDetailData.frequency || ''}</TextBox>
                ) : (
                  <Controller
                    name="frequency"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Frequency length should be less than 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.frequency}
                        helperText={errors.frequency?.message}
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
                <TextBox fieldName>Primary Voltage</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.voltage !== null ? formatFloatValue(technicalDetailData.voltage) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="voltage"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Primary Voltage'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.voltage}
                        helperText={errors.voltage?.message}
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
                <TextBox fieldName>Phase</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{technicalDetailData.phase || ''}</TextBox>
                ) : (
                  <Controller
                    name="phase"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Phase length should be less than 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.phase}
                        helperText={errors.phase?.message}
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
                <TextBox fieldName>Volts</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.volts !== null ? formatFloatValue(technicalDetailData.volts) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="volts"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Volts'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.volts}
                        helperText={errors.volts?.message}
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
          </TableBody>
        </SectionTable>
      </Box>
    );
  }
);

Transformer.displayName = 'Transformer';

export default Transformer;

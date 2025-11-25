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
  CombinerBoxDeviceTechnicalDetails,
  TechnicalDetailAttributes
} from '../../../../../../../../../../api';
import { useNotify } from '../../../../../../../../../../contexts/notifications/notifications';

interface CombinerBoxFormFields {
  dimensions: string | null;
  enclosure_type: string | null;
  input_circuits_max_count: string | null;
  max_output: string | null;
  weight: string | null;
}

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

const CombinerBox = React.forwardRef<DeviceTechnicalDetailsFormRef, DeviceTechnicalDetailsFormProps>(
  ({ mode, category, setMode, siteId, deviceId, technicalDetailsData: technicalDetailData, reflectFormState }, ref) => {
    const queryClient = useQueryClient();
    const notify = useNotify();

    const { handleSubmit, formState, control, reset } = useForm<CombinerBoxFormFields>({
      mode: 'onChange',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        dimensions:
          typeof technicalDetailData.dimensions === 'number'
            ? formatFloatValue(technicalDetailData.dimensions, true)
            : technicalDetailData.dimensions,
        enclosure_type:
          typeof technicalDetailData.enclosure_type === 'number'
            ? formatFloatValue(technicalDetailData.enclosure_type, true)
            : technicalDetailData.enclosure_type,
        input_circuits_max_count:
          typeof technicalDetailData.input_circuits_max_count === 'number'
            ? formatFloatValue(technicalDetailData.input_circuits_max_count, true)
            : technicalDetailData.input_circuits_max_count,
        max_output:
          typeof technicalDetailData.max_output === 'number'
            ? formatFloatValue(technicalDetailData.max_output, true)
            : technicalDetailData.max_output,
        weight:
          typeof technicalDetailData.weight === 'number'
            ? formatFloatValue(technicalDetailData.weight, true)
            : technicalDetailData.weight
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateDeviceTechnicalDetails } = useMutation({
      mutationFn: (attributes: CombinerBoxDeviceTechnicalDetails) => {
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
        dimensions:
          typeof technicalDetailData.dimensions === 'number'
            ? formatFloatValue(technicalDetailData.dimensions, true)
            : technicalDetailData.dimensions,
        enclosure_type:
          typeof technicalDetailData.enclosure_type === 'number'
            ? formatFloatValue(technicalDetailData.enclosure_type, true)
            : technicalDetailData.enclosure_type,
        input_circuits_max_count:
          typeof technicalDetailData.input_circuits_max_count === 'number'
            ? formatFloatValue(technicalDetailData.input_circuits_max_count, true)
            : technicalDetailData.input_circuits_max_count,
        max_output:
          typeof technicalDetailData.max_output === 'number'
            ? formatFloatValue(technicalDetailData.max_output, true)
            : technicalDetailData.max_output,
        weight:
          typeof technicalDetailData.weight === 'number'
            ? formatFloatValue(technicalDetailData.weight, true)
            : technicalDetailData.weight
      });
    }, [technicalDetailData, reset]);

    const onSubmit: SubmitHandler<CombinerBoxFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateDeviceTechnicalDetails({
            dimensions: data.dimensions ?? null,
            enclosure_type: data.enclosure_type ?? null,
            input_circuits_max_count: data.input_circuits_max_count
              ? Number.parseFloat(data.input_circuits_max_count.replaceAll(',', ''))
              : null,
            max_output: data.max_output ? Number.parseFloat(data.max_output.replaceAll(',', '')) : null,
            weight: data.weight ? Number.parseFloat(data.weight.replaceAll(',', '')) : null
          });
          notify(response.message || `Technical details was successfully updated.`);
          reset({
            dimensions: data.dimensions,
            enclosure_type: data.enclosure_type,
            input_circuits_max_count: data.input_circuits_max_count,
            max_output: data.max_output,
            weight: data.weight
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
                <TextBox fieldName>Enclosure Type</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{technicalDetailData.enclosure_type || ''}</TextBox>
                ) : (
                  <Controller
                    name="enclosure_type"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Enclosure Type length should be less than 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.enclosure_type}
                        helperText={errors.enclosure_type?.message}
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
                <TextBox fieldName>Dimensions</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{technicalDetailData.dimensions || ''}</TextBox>
                ) : (
                  <Controller
                    name="dimensions"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Dimensions length should be less than 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.dimensions}
                        helperText={errors.dimensions?.message}
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
                <TextBox fieldName>Weight (lbs)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.weight !== null ? formatFloatValue(technicalDetailData.weight) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="weight"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Weight'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.weight}
                        helperText={errors.weight?.message}
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
                <TextBox fieldName>Max Output</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.max_output !== null ? formatFloatValue(technicalDetailData.max_output) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="max_output"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Max Output'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.max_output}
                        helperText={errors.max_output?.message}
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
                <TextBox fieldName>Max # of Input Circuits</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.input_circuits_max_count !== null
                      ? formatFloatValue(technicalDetailData.input_circuits_max_count)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="input_circuits_max_count"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Max # of Input Circuits'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.input_circuits_max_count}
                        helperText={errors.input_circuits_max_count?.message}
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

CombinerBox.displayName = 'CombinerBox';

export default CombinerBox;

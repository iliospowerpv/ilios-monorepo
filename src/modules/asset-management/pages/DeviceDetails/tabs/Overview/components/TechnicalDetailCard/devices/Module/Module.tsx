import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import TableRow from '@mui/material/TableRow';
import TableBody from '@mui/material/TableBody';

import FormattedNumericInput from '../../../../../../../../../../components/common/FormattedNumericInput/FormattedNumericInput';
import FormattedNumericInputWithMinus from '../../../../../../../../../../components/common/FormattedNumericInput/FormattedNumericInputWithMinus';
import { FieldCell, TextBox, SectionTitle, SectionTable } from '../../TechnicalDetail.styles';
import { DeviceTechnicalDetailsFormProps, DeviceTechnicalDetailsFormRef } from '../../TechnicalDetailCard';
import formatFloatValue from '../../../../../../../../../../utils/formatters/formatFloatValue';
import {
  ApiClient,
  ModuleDeviceTechnicalDetails,
  ModuleFormFields,
  TechnicalDetailAttributes
} from '../../../../../../../../../../api';
import { useNotify } from '../../../../../../../../../../contexts/notifications/notifications';

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

const Module = React.forwardRef<DeviceTechnicalDetailsFormRef, DeviceTechnicalDetailsFormProps>(
  ({ mode, category, setMode, siteId, deviceId, technicalDetailsData: technicalDetailData, reflectFormState }, ref) => {
    const queryClient = useQueryClient();
    const notify = useNotify();

    const { handleSubmit, formState, control, reset } = useForm<ModuleFormFields>({
      mode: 'all',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        cable_and_connector: technicalDetailData.module_specs.cable_and_connector,
        frame: technicalDetailData.module_specs.frame,
        glass_type: technicalDetailData.module_specs.glass_type,
        module_kw: technicalDetailData.module_specs.module_kw,
        solar_cell_type: technicalDetailData.module_specs.solar_cell_type,
        solar_cells_per_module: technicalDetailData.module_specs.solar_cells_per_module,
        weight: technicalDetailData.module_specs.weight,
        mpp_current: technicalDetailData.power.mpp_current,
        mpp_voltage: technicalDetailData.power.mpp_voltage,
        mpp_watts: technicalDetailData.power.mpp_watts,
        power_output: technicalDetailData.power.power_output,
        system_voltage: technicalDetailData.power.system_voltage,
        temperature_coefficient: technicalDetailData.power.temperature_coefficient,
        watts_per_module: technicalDetailData.power.watts_per_module,
        year_1_degradation: technicalDetailData.power.year_1_degradation,
        annual_degradation: technicalDetailData.power.annual_degradation,
        max_power_tolerance: technicalDetailData.power.max_power_tolerance,
        min_power_tolerance: technicalDetailData.power.min_power_tolerance,
        power_thermal_coefficient: technicalDetailData.power.power_thermal_coefficient
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateDeviceTechnicalDetails } = useMutation({
      mutationFn: (attributes: ModuleDeviceTechnicalDetails) => {
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
        cable_and_connector: technicalDetailData.module_specs.cable_and_connector,
        frame: technicalDetailData.module_specs.frame,
        glass_type: technicalDetailData.module_specs.glass_type,
        module_kw: technicalDetailData.module_specs.module_kw,
        solar_cell_type: technicalDetailData.module_specs.solar_cell_type,
        solar_cells_per_module: technicalDetailData.module_specs.solar_cells_per_module,
        weight: technicalDetailData.module_specs.weight,
        mpp_current: technicalDetailData.power.mpp_current,
        mpp_voltage: technicalDetailData.power.mpp_voltage,
        mpp_watts: technicalDetailData.power.mpp_watts,
        power_output: technicalDetailData.power.power_output,
        system_voltage: technicalDetailData.power.system_voltage,
        temperature_coefficient: technicalDetailData.power.temperature_coefficient,
        watts_per_module: technicalDetailData.power.watts_per_module,
        year_1_degradation: technicalDetailData.power.year_1_degradation,
        annual_degradation: technicalDetailData.power.annual_degradation,
        max_power_tolerance: technicalDetailData.power.max_power_tolerance,
        min_power_tolerance: technicalDetailData.power.min_power_tolerance,
        power_thermal_coefficient: technicalDetailData.power.power_thermal_coefficient
      });
    }, [technicalDetailData, reset]);

    const onSubmit: SubmitHandler<ModuleFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateDeviceTechnicalDetails({
            module_specs: {
              cable_and_connector: data.cable_and_connector ?? null,
              frame: data.frame ?? null,
              glass_type: data.glass_type ?? null,
              module_kw: data.module_kw ?? null,
              solar_cell_type: data.solar_cell_type ?? null,
              solar_cells_per_module: data.solar_cells_per_module ?? null,
              weight: data.weight ?? null
            },
            power: {
              mpp_current: data.mpp_current ?? null,
              mpp_voltage: data.mpp_voltage ?? null,
              mpp_watts: data.mpp_watts ?? null,
              power_output: data.power_output ?? null,
              system_voltage: data.system_voltage ?? null,
              temperature_coefficient: data.temperature_coefficient ?? null,
              watts_per_module: data.watts_per_module ?? null,
              year_1_degradation: data.year_1_degradation ?? null,
              annual_degradation: data.annual_degradation ?? null,
              max_power_tolerance: data.max_power_tolerance ?? null,
              min_power_tolerance: data.min_power_tolerance ?? null,
              power_thermal_coefficient: data.power_thermal_coefficient ?? null
            }
          });
          notify(response.message || `Technical details was successfully updated.`);
          reset({
            cable_and_connector: data.cable_and_connector,
            frame: data.frame,
            glass_type: data.glass_type,
            module_kw: data.module_kw,
            solar_cell_type: data.solar_cell_type,
            solar_cells_per_module: data.solar_cells_per_module,
            weight: data.weight,
            mpp_current: data.mpp_current,
            mpp_voltage: data.mpp_voltage,
            mpp_watts: data.mpp_watts,
            power_output: data.power_output,
            system_voltage: data.system_voltage,
            temperature_coefficient: data.temperature_coefficient,
            watts_per_module: data.watts_per_module,
            year_1_degradation: data.year_1_degradation,
            annual_degradation: data.annual_degradation,
            max_power_tolerance: data.max_power_tolerance,
            min_power_tolerance: data.min_power_tolerance,
            power_thermal_coefficient: data.power_thermal_coefficient
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
        <SectionTitle variant="h6">Module Specs</SectionTitle>
        <SectionTable size="small">
          <TableBody>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Weight (lbs)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.module_specs.weight !== null
                      ? formatFloatValue(technicalDetailData.module_specs.weight)
                      : ''}
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
                          inputComponent: FormattedNumericInputWithMinus as any,
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
                <TextBox fieldName>Module (kW)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.module_specs.module_kw !== null
                      ? formatFloatValue(technicalDetailData.module_specs.module_kw)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="module_kw"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Module kW'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.module_kw}
                        helperText={errors.module_kw?.message}
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
                <TextBox fieldName>Solar Cells per Module</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.module_specs.solar_cells_per_module !== null
                      ? formatFloatValue(technicalDetailData.module_specs.solar_cells_per_module)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="solar_cells_per_module"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Solar Cells per Module'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.solar_cells_per_module}
                        helperText={errors.solar_cells_per_module?.message}
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
                <TextBox fieldName>Solar Cell Type</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{technicalDetailData.module_specs.solar_cell_type || ''}</TextBox>
                ) : (
                  <Controller
                    name="solar_cell_type"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Solar Cell Type length should be less than 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.solar_cell_type}
                        helperText={errors.solar_cell_type?.message}
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
                <TextBox fieldName>Glass Type</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{technicalDetailData.module_specs.glass_type || ''}</TextBox>
                ) : (
                  <Controller
                    name="glass_type"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Glass Type length should be less than 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.glass_type}
                        helperText={errors.glass_type?.message}
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
                <TextBox fieldName>Cable & Connector</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{technicalDetailData.module_specs.cable_and_connector || ''}</TextBox>
                ) : (
                  <Controller
                    name="cable_and_connector"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Cable & Connector length should be less than 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.cable_and_connector}
                        helperText={errors.cable_and_connector?.message}
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
                <TextBox fieldName>Frame</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{technicalDetailData.module_specs.frame || ''}</TextBox>
                ) : (
                  <Controller
                    name="frame"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Cable & Connector length should be less than 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.frame}
                        helperText={errors.frame?.message}
                        disabled={isSubmitting}
                        value={value || ''}
                        inputRef={ref}
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
        <SectionTitle variant="h6">Power</SectionTitle>
        <SectionTable size="small">
          <TableBody>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>System Voltage (V)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.power.system_voltage !== null
                      ? formatFloatValue(technicalDetailData.power.system_voltage)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="system_voltage"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for System Voltage (V)'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.system_voltage}
                        helperText={errors.system_voltage?.message}
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
                <TextBox fieldName>Power Output (W)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.power.power_output !== null
                      ? formatFloatValue(technicalDetailData.power.power_output)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="power_output"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Power Output (W)'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.power_output}
                        helperText={errors.power_output?.message}
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
                <TextBox fieldName>MPP Voltage</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.power.mpp_voltage !== null
                      ? formatFloatValue(technicalDetailData.power.mpp_voltage)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="mpp_voltage"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for MPP Voltage'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.mpp_voltage}
                        helperText={errors.mpp_voltage?.message}
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
                <TextBox fieldName>MPP Current</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.power.mpp_current !== null
                      ? formatFloatValue(technicalDetailData.power.mpp_current)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="mpp_current"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for MPP Current'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.mpp_current}
                        helperText={errors.mpp_current?.message}
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
                <TextBox fieldName>MPP Watts</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.power.mpp_watts !== null
                      ? formatFloatValue(technicalDetailData.power.mpp_watts)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="mpp_watts"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for MPP Watts'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.mpp_watts}
                        helperText={errors.mpp_watts?.message}
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
                <TextBox fieldName>Temperature Coefficient (%)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.power.temperature_coefficient !== null
                      ? formatFloatValue(technicalDetailData.power.temperature_coefficient)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="temperature_coefficient"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Temperature Coefficient'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.temperature_coefficient}
                        helperText={errors.temperature_coefficient?.message}
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
                <TextBox fieldName>Watts per Module</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.power.watts_per_module !== null
                      ? formatFloatValue(technicalDetailData.power.watts_per_module)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="watts_per_module"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Watts per Module'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.watts_per_module}
                        helperText={errors.watts_per_module?.message}
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
                <TextBox fieldName>Thermal Coefficient of Power</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.power.power_thermal_coefficient !== null
                      ? formatFloatValue(technicalDetailData.power.power_thermal_coefficient)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="power_thermal_coefficient"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return 'Thermal Coefficient of Power is required field.';
                        if ((value as unknown as string).length > 100)
                          return 'Thermal Coefficient of Power length should not exceed 100 characters.';
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Thermal Coefficient of Power'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.power_thermal_coefficient}
                        helperText={errors.power_thermal_coefficient?.message}
                        multiline
                        required
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          inputComponent: FormattedNumericInputWithMinus as any,
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
                <TextBox fieldName>Power Tolerance Min (W)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.power.min_power_tolerance !== null
                      ? formatFloatValue(technicalDetailData.power.min_power_tolerance)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="min_power_tolerance"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return 'Power Tolerance Min is required field.';
                        if ((value as unknown as string).length > 100)
                          return 'Power Tolerance Min length should not exceed 100 characters.';
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        const parsedNumber = Number.parseFloat(withoutThousandSeparators);
                        if (Number.isNaN(parsedNumber))
                          return 'Invalid number provided as a value for Power Tolerance Min';

                        return parsedNumber > 0 ? 'Power Tolerance Min must be less than or equal to 0' : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.min_power_tolerance}
                        helperText={errors.min_power_tolerance?.message}
                        multiline
                        required
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          inputComponent: FormattedNumericInputWithMinus as any,
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
                <TextBox fieldName>Power Tolerance Max (W)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.power.max_power_tolerance !== null
                      ? formatFloatValue(technicalDetailData.power.max_power_tolerance)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="max_power_tolerance"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return 'Power Tolerance Max is required field.';
                        if ((value as unknown as string).length > 100)
                          return 'Power Tolerance Max length should not exceed 100 characters.';
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        const parsedNumber = Number.parseFloat(withoutThousandSeparators);
                        if (Number.isNaN(parsedNumber))
                          return 'Invalid number provided as a value for Power Tolerance Max';

                        return parsedNumber < 0 ? 'Power Tolerance Max must be greater than or equal to 0' : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.max_power_tolerance}
                        helperText={errors.max_power_tolerance?.message}
                        multiline
                        required
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          inputComponent: FormattedNumericInputWithMinus as any,
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
                <TextBox fieldName>Year 1 Degradation %</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.power.year_1_degradation !== null
                      ? formatFloatValue(technicalDetailData.power.year_1_degradation)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="year_1_degradation"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return 'Year 1 Degradation is required field.';
                        if ((value as unknown as string).length > 100)
                          return 'Year 1 Degradation length should not exceed 100 characters.';
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Year 1 Degradation'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.year_1_degradation}
                        helperText={errors.year_1_degradation?.message}
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
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Annual Degradation %</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.power.annual_degradation !== null
                      ? formatFloatValue(technicalDetailData.power.annual_degradation)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="annual_degradation"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return 'Annual Degradation is required field.';
                        if ((value as unknown as string).length > 100)
                          return 'Annual Degradation length should not exceed 100 characters.';
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Annual Degradation'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.annual_degradation}
                        helperText={errors.annual_degradation?.message}
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
          </TableBody>
        </SectionTable>
      </Box>
    );
  }
);

Module.displayName = 'Module';

export default Module;

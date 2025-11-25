import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import TableRow from '@mui/material/TableRow';
import TableBody from '@mui/material/TableBody';

import FormattedNumericInput from '../../../../../../../../../../components/common/FormattedNumericInput/FormattedNumericInput';
import FormattedIntegerNumericInput from '../../../../../../../../../../components/common/FormattedIntegerNumericInput/FormattedIntegerNumericInput';
import { FieldCell, TextBox, SectionTitle, SectionTable, StyledSelectItem } from '../../TechnicalDetail.styles';
import { DeviceTechnicalDetailsFormProps, DeviceTechnicalDetailsFormRef } from '../../TechnicalDetailCard';
import formatFloatValue from '../../../../../../../../../../utils/formatters/formatFloatValue';
import {
  ApiClient,
  InverterDeviceTechnicalDetails,
  InverterFormFields,
  TechnicalDetailAttributes
} from '../../../../../../../../../../api';
import { useNotify } from '../../../../../../../../../../contexts/notifications/notifications';

const intFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
  useGrouping: false
});
const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

const Inverter = React.forwardRef<DeviceTechnicalDetailsFormRef, DeviceTechnicalDetailsFormProps>(
  ({ mode, category, setMode, siteId, deviceId, technicalDetailsData: technicalDetailData, reflectFormState }, ref) => {
    const queryClient = useQueryClient();
    const notify = useNotify();

    const { handleSubmit, formState, control, reset } = useForm<InverterFormFields>({
      mode: 'onChange',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        derate: technicalDetailData.array.derate,
        integrated_combiners: technicalDetailData.array.integrated_combiners,
        modules_per_string: technicalDetailData.array.modules_per_string,
        number_of_strings: technicalDetailData.array.number_of_strings,
        yearly_degradation: technicalDetailData.array.yearly_degradation,
        ip_address: technicalDetailData.communication.ip_address,
        port:
          technicalDetailData.communication.port !== null
            ? intFormatter.format(technicalDetailData.communication.port)
            : technicalDetailData.communication.port,
        serial_mode: technicalDetailData.communication.serial_mode,
        baud:
          technicalDetailData.communication.baud !== null
            ? intFormatter.format(technicalDetailData.communication.baud)
            : technicalDetailData.communication.baud,
        watts_per_module: technicalDetailData.module.watts_per_module,
        mpp_voltage: technicalDetailData.module.mpp_voltage,
        mpp_current: technicalDetailData.module.mpp_current,
        mpp_watts: technicalDetailData.module.mpp_watts,
        temperature_coefficient: technicalDetailData.module.temperature_coefficient,
        ac_max_output: technicalDetailData.power.ac_max_output,
        ac_power: technicalDetailData.power.ac_power,
        dc_max_input: technicalDetailData.power.dc_max_input,
        dc_power: technicalDetailData.power.dc_power,
        rated_output: technicalDetailData.power.rated_output,
        standby_power: technicalDetailData.power.standby_power,
        cec_efficiency: technicalDetailData.power.cec_efficiency,
        pv_modules_number: technicalDetailData.power.pv_modules_number
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateDeviceTechnicalDetails } = useMutation({
      mutationFn: (attributes: InverterDeviceTechnicalDetails) => {
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
        derate: technicalDetailData.array.derate,
        integrated_combiners: technicalDetailData.array.integrated_combiners,
        modules_per_string: technicalDetailData.array.modules_per_string,
        number_of_strings: technicalDetailData.array.number_of_strings,
        yearly_degradation: technicalDetailData.array.yearly_degradation,
        ip_address: technicalDetailData.communication.ip_address,
        port:
          technicalDetailData.communication.port !== null
            ? intFormatter.format(technicalDetailData.communication.port)
            : technicalDetailData.communication.port,
        serial_mode: technicalDetailData.communication.serial_mode,
        baud:
          technicalDetailData.communication.baud !== null
            ? intFormatter.format(technicalDetailData.communication.baud)
            : technicalDetailData.communication.baud,
        watts_per_module: technicalDetailData.module.watts_per_module,
        mpp_voltage: technicalDetailData.module.mpp_voltage,
        mpp_current: technicalDetailData.module.mpp_current,
        mpp_watts: technicalDetailData.module.mpp_watts,
        temperature_coefficient: technicalDetailData.module.temperature_coefficient,
        ac_max_output: technicalDetailData.power.ac_max_output,
        ac_power: technicalDetailData.power.ac_power,
        dc_max_input: technicalDetailData.power.dc_max_input,
        dc_power: technicalDetailData.power.dc_power,
        rated_output: technicalDetailData.power.rated_output,
        standby_power: technicalDetailData.power.standby_power,
        cec_efficiency: technicalDetailData.power.cec_efficiency,
        pv_modules_number: technicalDetailData.power.pv_modules_number
      });
    }, [technicalDetailData, reset]);

    const onSubmit: SubmitHandler<InverterFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateDeviceTechnicalDetails({
            array: {
              derate: data.derate ?? null,
              integrated_combiners: data.integrated_combiners ?? null,
              modules_per_string: data.modules_per_string ?? null,
              number_of_strings: data.number_of_strings ?? null,
              yearly_degradation: data.yearly_degradation ?? null
            },
            communication: {
              ip_address: data.ip_address ?? null,
              port: data.port !== null ? Number.parseInt(data.port) : null,
              serial_mode: data.serial_mode ?? null,
              baud: data.baud !== null ? Number.parseInt(data.baud) : null
            },
            module: {
              watts_per_module: data.watts_per_module ?? null,
              mpp_voltage: data.mpp_voltage ?? null,
              mpp_current: data.mpp_current ?? null,
              mpp_watts: data.mpp_watts ?? null,
              temperature_coefficient: data.temperature_coefficient ?? null
            },
            power: {
              ac_max_output: data.ac_max_output ?? null,
              ac_power: data.ac_power ?? null,
              dc_max_input: data.dc_max_input ?? null,
              dc_power: data.dc_power ?? null,
              rated_output: data.rated_output ?? null,
              standby_power: data.standby_power ?? null,
              cec_efficiency: data.cec_efficiency ?? null,
              pv_modules_number: data.pv_modules_number ?? null
            }
          });
          notify(response.message || `Technical details was successfully updated.`);
          reset({
            derate: data.derate,
            integrated_combiners: data.integrated_combiners,
            modules_per_string: data.modules_per_string,
            number_of_strings: data.number_of_strings,
            yearly_degradation: data.yearly_degradation,
            ip_address: data.ip_address,
            port: data.port,
            serial_mode: data.serial_mode,
            baud: data.baud,
            watts_per_module: data.watts_per_module,
            mpp_voltage: data.mpp_voltage,
            mpp_current: data.mpp_current,
            mpp_watts: data.mpp_watts,
            temperature_coefficient: data.temperature_coefficient,
            ac_max_output: data.ac_max_output,
            ac_power: data.ac_power,
            dc_max_input: data.dc_max_input,
            dc_power: data.dc_power,
            rated_output: data.rated_output,
            standby_power: data.standby_power,
            cec_efficiency: data.cec_efficiency,
            pv_modules_number: data.pv_modules_number
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
        <SectionTitle variant="h6">Power</SectionTitle>
        <SectionTable size="small">
          <TableBody>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>CEC Efficiency (%)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.power.cec_efficiency !== null
                      ? formatFloatValue(technicalDetailData.power.cec_efficiency)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="cec_efficiency"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return 'CEC Efficiency is required field.';
                        if ((value as unknown as string).length > 100)
                          return 'CEC Efficiency length should not exceed 100 characters.';
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for CEC Efficiency'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.cec_efficiency}
                        helperText={errors.cec_efficiency?.message}
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
                <TextBox fieldName>Number of PV modules per Inverter</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{technicalDetailData.power.pv_modules_number ?? ''}</TextBox>
                ) : (
                  <Controller
                    name="pv_modules_number"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return 'Number of PV modules per Inverter is required field.';
                        if ((value as unknown as string).length > 100)
                          return 'Number of PV modules per Inverter length should not exceed 100 characters.';
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Number of PV modules per Inverter'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.pv_modules_number}
                        helperText={errors.pv_modules_number?.message}
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
                <TextBox fieldName>DC Power (kW)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.power.dc_power !== null
                      ? formatFloatValue(technicalDetailData.power.dc_power)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="dc_power"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for DC Power'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.dc_power}
                        helperText={errors.dc_power?.message}
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
                <TextBox fieldName>DC Max Input Voltage (V)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.power.dc_max_input !== null
                      ? formatFloatValue(technicalDetailData.power.dc_max_input)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="dc_max_input"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for DC Max Input Voltage'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.dc_max_input}
                        helperText={errors.dc_max_input?.message}
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
                <TextBox fieldName>AC Power (kW)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.power.ac_power !== null
                      ? formatFloatValue(technicalDetailData.power.ac_power)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="ac_power"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for AC Power'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.ac_power}
                        helperText={errors.ac_power?.message}
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
                <TextBox fieldName>AC Max Output Voltage (V)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.power.ac_max_output !== null
                      ? formatFloatValue(technicalDetailData.power.ac_max_output)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="ac_max_output"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for AC Max Output Voltage'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.ac_max_output}
                        helperText={errors.ac_max_output?.message}
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
                <TextBox fieldName>Standby Power (Watts)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.power.standby_power !== null
                      ? formatFloatValue(technicalDetailData.power.standby_power)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="standby_power"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Standby Power'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.standby_power}
                        helperText={errors.standby_power?.message}
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
                <TextBox fieldName>Rated Output (kVA)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.power.rated_output !== null
                      ? formatFloatValue(technicalDetailData.power.rated_output)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="rated_output"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Rated Output'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.rated_output}
                        helperText={errors.rated_output?.message}
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
        <SectionTitle variant="h6">Array</SectionTitle>
        <SectionTable size="small">
          <TableBody>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Number of Strings</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.array.number_of_strings !== null
                      ? formatFloatValue(technicalDetailData.array.number_of_strings)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="number_of_strings"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Number of Strings'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.number_of_strings}
                        helperText={errors.number_of_strings?.message}
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
                <TextBox fieldName>Modules per String</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.array.modules_per_string !== null
                      ? formatFloatValue(technicalDetailData.array.modules_per_string)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="modules_per_string"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Modules per String'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.modules_per_string}
                        helperText={errors.modules_per_string?.message}
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
                <TextBox fieldName>Integrated Combiners</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{technicalDetailData.array.integrated_combiners || ''}</TextBox>
                ) : (
                  <Controller
                    name="integrated_combiners"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.integrated_combiners}
                        helperText={errors.integrated_combiners?.message}
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
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Yearly Degredation</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.array.yearly_degradation !== null
                      ? formatFloatValue(technicalDetailData.array.yearly_degradation)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="yearly_degradation"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Yearly Degredation'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.yearly_degradation}
                        helperText={errors.yearly_degradation?.message}
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
                <TextBox fieldName>Derate</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.array.derate !== null
                      ? formatFloatValue(technicalDetailData.array.derate)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="derate"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Derate'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.derate}
                        helperText={errors.derate?.message}
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
        <SectionTitle variant="h6">Module</SectionTitle>
        <SectionTable size="small">
          <TableBody>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Watts per Module</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.module.watts_per_module !== null
                      ? formatFloatValue(technicalDetailData.module.watts_per_module)
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
                <TextBox fieldName>MPP Voltage</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {technicalDetailData.module.mpp_voltage !== null
                      ? formatFloatValue(technicalDetailData.module.mpp_voltage)
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
                    {technicalDetailData.module.mpp_current !== null
                      ? formatFloatValue(technicalDetailData.module.mpp_current)
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
                    {technicalDetailData.module.mpp_watts !== null
                      ? formatFloatValue(technicalDetailData.module.mpp_watts)
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
                    {technicalDetailData.module.temperature_coefficient !== null
                      ? formatFloatValue(technicalDetailData.module.temperature_coefficient)
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
          </TableBody>
        </SectionTable>
      </Box>
    );
  }
);

Inverter.displayName = 'Inverter';

export default Inverter;

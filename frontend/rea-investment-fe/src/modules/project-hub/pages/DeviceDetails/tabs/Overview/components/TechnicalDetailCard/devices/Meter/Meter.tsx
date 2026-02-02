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
import { ApiClient, MeterDeviceTechnicalDetails, TechnicalDetailAttributes } from '../../../../../../../../../../api';
import { useNotify } from '../../../../../../../../../../contexts/notifications/notifications';
import formatFloatValue from '../../../../../../../../../../utils/formatters/formatFloatValue';

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

interface MeterFormFields {
  capacity: string | null;
  inverters: string | null;
  power_scale_factor: string | null;
  energy_scale_factor: string | null;
  swap_delivered_and_received: string | null;
  gross_energy: string | null;
  ip_address: string | null;
  unit_id: string | null;
  sample_data_kw: string | null;
  sample_data_kwh_net: string | null;
  sample_data_kwh_received: string | null;
  sample_data_kwh_delivered: string | null;
  max_power_kw: string | null;
  max_voltage: string | null;
  max_current_per_phase: string | null;
  ac: string | null;
}

const Meter = React.forwardRef<DeviceTechnicalDetailsFormRef, DeviceTechnicalDetailsFormProps>(
  ({ mode, category, setMode, siteId, deviceId, technicalDetailsData: technicalDetailData, reflectFormState }, ref) => {
    const { general, communication, scale_factor, sample_date, data_range } =
      technicalDetailData as MeterDeviceTechnicalDetails;

    const queryClient = useQueryClient();
    const notify = useNotify();

    const { handleSubmit, formState, control, reset } = useForm<MeterFormFields>({
      mode: 'onChange',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        capacity: typeof general.capacity === 'number' ? formatFloatValue(general.capacity, true) : general.capacity,
        inverters:
          typeof general.inverters === 'number' ? formatFloatValue(general.inverters, true) : general.inverters,
        power_scale_factor:
          typeof scale_factor.power === 'number' ? formatFloatValue(scale_factor.power, true) : scale_factor.power,
        energy_scale_factor:
          typeof scale_factor.energy === 'number' ? formatFloatValue(scale_factor.energy, true) : scale_factor.energy,
        swap_delivered_and_received: scale_factor.swap_delivered_received,
        gross_energy: scale_factor.gross_energy,
        ip_address: communication.ip_address,
        unit_id:
          typeof communication.unit_id === 'number' ? Number(communication.unit_id).toFixed(0) : communication.unit_id,
        sample_data_kw: typeof sample_date.kw === 'number' ? formatFloatValue(sample_date.kw, true) : sample_date.kw,
        sample_data_kwh_net:
          typeof sample_date.kwh_net === 'number' ? formatFloatValue(sample_date.kwh_net, true) : sample_date.kwh_net,
        sample_data_kwh_received:
          typeof sample_date.kwh_received === 'number'
            ? formatFloatValue(sample_date.kwh_received, true)
            : sample_date.kwh_received,
        sample_data_kwh_delivered:
          typeof sample_date.kwh_delivered === 'number'
            ? formatFloatValue(sample_date.kwh_delivered, true)
            : sample_date.kwh_delivered,
        max_power_kw:
          typeof data_range.max_power === 'number'
            ? formatFloatValue(data_range.max_power, true)
            : data_range.max_power,
        max_voltage:
          typeof data_range.max_voltage === 'number'
            ? formatFloatValue(data_range.max_voltage, true)
            : data_range.max_voltage,
        max_current_per_phase:
          typeof data_range.max_current_per_phase === 'number'
            ? formatFloatValue(data_range.max_current_per_phase, true)
            : data_range.max_current_per_phase,
        ac: data_range.ac
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateDeviceTechnicalDetails } = useMutation({
      mutationFn: (attributes: MeterDeviceTechnicalDetails) => {
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
        capacity: typeof general.capacity === 'number' ? formatFloatValue(general.capacity, true) : general.capacity,
        inverters:
          typeof general.inverters === 'number' ? formatFloatValue(general.inverters, true) : general.inverters,
        power_scale_factor:
          typeof scale_factor.power === 'number' ? formatFloatValue(scale_factor.power, true) : scale_factor.power,
        energy_scale_factor:
          typeof scale_factor.energy === 'number' ? formatFloatValue(scale_factor.energy, true) : scale_factor.energy,
        swap_delivered_and_received: scale_factor.swap_delivered_received,
        gross_energy: scale_factor.gross_energy,
        ip_address: communication.ip_address,
        unit_id:
          typeof communication.unit_id === 'number' ? Number(communication.unit_id).toFixed(0) : communication.unit_id,
        sample_data_kw: typeof sample_date.kw === 'number' ? formatFloatValue(sample_date.kw, true) : sample_date.kw,
        sample_data_kwh_net:
          typeof sample_date.kwh_net === 'number' ? formatFloatValue(sample_date.kwh_net, true) : sample_date.kwh_net,
        sample_data_kwh_received:
          typeof sample_date.kwh_received === 'number'
            ? formatFloatValue(sample_date.kwh_received, true)
            : sample_date.kwh_received,
        sample_data_kwh_delivered:
          typeof sample_date.kwh_delivered === 'number'
            ? formatFloatValue(sample_date.kwh_delivered, true)
            : sample_date.kwh_delivered,
        max_power_kw:
          typeof data_range.max_power === 'number'
            ? formatFloatValue(data_range.max_power, true)
            : data_range.max_power,
        max_voltage:
          typeof data_range.max_voltage === 'number'
            ? formatFloatValue(data_range.max_voltage, true)
            : data_range.max_voltage,
        max_current_per_phase:
          typeof data_range.max_current_per_phase === 'number'
            ? formatFloatValue(data_range.max_current_per_phase, true)
            : data_range.max_current_per_phase,
        ac: data_range.ac
      });
    }, [general, scale_factor, communication, sample_date, data_range, reset]);

    const onSubmit: SubmitHandler<MeterFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateDeviceTechnicalDetails({
            general: {
              capacity: data.capacity ? Number.parseFloat(data.capacity.replaceAll(',', '')) : null,
              inverters: data.inverters ? Number.parseFloat(data.inverters.replaceAll(',', '')) : null
            },
            communication: {
              ip_address: data.ip_address ?? null,
              unit_id: data.unit_id ? Number.parseInt(data.unit_id) : null
            },
            scale_factor: {
              power: data.power_scale_factor ? Number.parseFloat(data.power_scale_factor.replaceAll(',', '')) : null,
              energy: data.energy_scale_factor ? Number.parseFloat(data.energy_scale_factor.replaceAll(',', '')) : null,
              swap_delivered_received: data.swap_delivered_and_received ?? null,
              gross_energy: data.gross_energy ?? null
            },
            sample_date: {
              kw: data.sample_data_kw ? Number.parseFloat(data.sample_data_kw.replaceAll(',', '')) : null,
              kwh_net: data.sample_data_kwh_net
                ? Number.parseFloat(data.sample_data_kwh_net.replaceAll(',', ''))
                : null,
              kwh_received: data.sample_data_kwh_received
                ? Number.parseFloat(data.sample_data_kwh_received.replaceAll(',', ''))
                : null,
              kwh_delivered: data.sample_data_kwh_delivered
                ? Number.parseFloat(data.sample_data_kwh_delivered.replaceAll(',', ''))
                : null
            },
            data_range: {
              max_power: data.max_power_kw ? Number.parseFloat(data.max_power_kw.replaceAll(',', '')) : null,
              max_voltage: data.max_voltage ? Number.parseFloat(data.max_voltage.replaceAll(',', '')) : null,
              max_current_per_phase: data.max_current_per_phase
                ? Number.parseFloat(data.max_current_per_phase.replaceAll(',', ''))
                : null,
              ac: data.ac
            }
          });
          notify(response.message || `Technical details were successfully updated.`);
          reset({
            capacity: data.capacity,
            inverters: data.inverters,
            power_scale_factor: data.power_scale_factor,
            energy_scale_factor: data.energy_scale_factor,
            swap_delivered_and_received: data.swap_delivered_and_received,
            gross_energy: data.gross_energy,
            ip_address: data.ip_address,
            unit_id: data.unit_id,
            sample_data_kw: data.sample_data_kw,
            sample_data_kwh_net: data.sample_data_kwh_net,
            sample_data_kwh_received: data.sample_data_kwh_received,
            sample_data_kwh_delivered: data.sample_data_kwh_delivered,
            max_power_kw: data.max_power_kw,
            max_voltage: data.max_voltage,
            max_current_per_phase: data.max_current_per_phase,
            ac: data.ac
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
                <TextBox fieldName>Capacity (kW)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{general.capacity !== null ? formatFloatValue(general.capacity) : ''}</TextBox>
                ) : (
                  <Controller
                    name="capacity"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Capacity (kW)'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.capacity}
                        helperText={errors.capacity?.message}
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
                <TextBox fieldName>Inverters (kW)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{general.inverters !== null ? formatFloatValue(general.inverters) : ''}</TextBox>
                ) : (
                  <Controller
                    name="inverters"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Inverters (kW)'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.inverters}
                        helperText={errors.inverters?.message}
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
                  <TextBox>{communication.ip_address}</TextBox>
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
                <TextBox fieldName>Unit ID</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{communication.unit_id}</TextBox>
                ) : (
                  <Controller
                    name="unit_id"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        return Number.isNaN(Number.parseInt(value))
                          ? 'Invalid number provided as a value for Unit ID'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.unit_id}
                        helperText={errors.unit_id?.message}
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
        <SectionTitle variant="h6">Scale Factor</SectionTitle>
        <SectionTable size="small">
          <TableBody>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Power Scale Factor</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{scale_factor.power !== null ? formatFloatValue(scale_factor.power) : ''}</TextBox>
                ) : (
                  <Controller
                    name="power_scale_factor"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Power Scale Factor'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.power_scale_factor}
                        helperText={errors.power_scale_factor?.message}
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
                <TextBox fieldName>Energy Scale Factor</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{scale_factor.energy !== null ? formatFloatValue(scale_factor.energy) : ''}</TextBox>
                ) : (
                  <Controller
                    name="energy_scale_factor"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Energy Scale Factor'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.energy_scale_factor}
                        helperText={errors.energy_scale_factor?.message}
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
                <TextBox fieldName>Swap Delivered and Received</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'edit' ? 'left' : 'right'}>
                {mode === 'view' ? (
                  <TextBox>{scale_factor.swap_delivered_received || ''}</TextBox>
                ) : (
                  <Controller
                    name="swap_delivered_and_received"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.swap_delivered_and_received}
                        helperText={errors.swap_delivered_and_received?.message}
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
                <TextBox fieldName>Gross Energy</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{scale_factor.gross_energy || ''}</TextBox>
                ) : (
                  <Controller
                    name="gross_energy"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Gross energy length should not exceed the limit of 100 characters'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.gross_energy}
                        helperText={errors.gross_energy?.message}
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
        <SectionTitle variant="h6">Sample Data</SectionTitle>
        <SectionTable size="small">
          <TableBody>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>kW</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{sample_date.kw !== null ? formatFloatValue(sample_date.kw) : ''}</TextBox>
                ) : (
                  <Controller
                    name="sample_data_kw"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for kW'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.sample_data_kw}
                        helperText={errors.sample_data_kw?.message}
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
                <TextBox fieldName>kWh Net</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{sample_date.kwh_net !== null ? formatFloatValue(sample_date.kwh_net) : ''}</TextBox>
                ) : (
                  <Controller
                    name="sample_data_kwh_net"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for kWh Net'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.sample_data_kwh_net}
                        helperText={errors.sample_data_kwh_net?.message}
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
                <TextBox fieldName>kWh Received</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {sample_date.kwh_received !== null ? formatFloatValue(sample_date.kwh_received) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="sample_data_kwh_received"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for kWh Received'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.sample_data_kwh_received}
                        helperText={errors.sample_data_kwh_received?.message}
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
                <TextBox fieldName>kWh Delivered</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {sample_date.kwh_delivered !== null ? formatFloatValue(sample_date.kwh_delivered) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="sample_data_kwh_delivered"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for kWh Delivered'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.sample_data_kwh_delivered}
                        helperText={errors.sample_data_kwh_delivered?.message}
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
        <SectionTitle variant="h6">Data Range</SectionTitle>
        <SectionTable size="small">
          <TableBody>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Max Power (kW)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{data_range.max_power !== null ? formatFloatValue(data_range.max_power) : ''}</TextBox>
                ) : (
                  <Controller
                    name="max_power_kw"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Max power (kW)'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.max_power_kw}
                        helperText={errors.max_power_kw?.message}
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
                <TextBox fieldName>Max Voltage</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{data_range.max_voltage !== null ? formatFloatValue(data_range.max_voltage) : ''}</TextBox>
                ) : (
                  <Controller
                    name="max_voltage"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Max Voltage'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.max_voltage}
                        helperText={errors.max_voltage?.message}
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
                <TextBox fieldName>Max Current (per Phase)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {data_range.max_current_per_phase ? formatFloatValue(data_range.max_current_per_phase) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="max_current_per_phase"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Max Current (per phase)'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.max_current_per_phase}
                        helperText={errors.max_current_per_phase?.message}
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
                <TextBox fieldName>AC</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{data_range.ac || ''}</TextBox>
                ) : (
                  <Controller
                    name="ac"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'AC length should not exceed the limit of 100 characters'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.ac}
                        helperText={errors.ac?.message}
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

Meter.displayName = 'Meter';

export default Meter;

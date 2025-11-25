import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import TableRow from '@mui/material/TableRow';
import TableBody from '@mui/material/TableBody';

import FormattedNumericInput from '../../../../../../../../../../components/common/FormattedNumericInput/FormattedNumericInput';
import FormattedIntegerNumericInput from '../../../../../../../../../../components/common/FormattedIntegerNumericInput/FormattedIntegerNumericInput';
import FormattedIntegerNegativeAllowedNumericInput from '../../../../../../../../../../components/common/FormattedIntegerNegativeAllowedNumericInput/FormattedIntegerNegativeAllowedNumericInput';
import { FieldCell, TextBox, SectionTitle, SectionTable, StyledSelectItem } from '../../TechnicalDetail.styles';
import { DeviceTechnicalDetailsFormProps, DeviceTechnicalDetailsFormRef } from '../../TechnicalDetailCard';
import {
  ApiClient,
  WeatherStationTechnicalDetails,
  TechnicalDetailAttributes
} from '../../../../../../../../../../api';
import { useNotify } from '../../../../../../../../../../contexts/notifications/notifications';
import formatFloatValue from '../../../../../../../../../../utils/formatters/formatFloatValue';

const floatFormatter = new Intl.NumberFormat('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
const intFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
  useGrouping: false
});
const temparatureFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
  signDisplay: 'exceptZero',
  useGrouping: false
});

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

interface WeatherStationFormFields {
  ip_address: null | string;
  port: null | string;
  serial_mode: null | string;
  baud: null | string;
  sensors_wind: null | string;
  sensors_humidity: null | string;
  sensors_barometer: null | string;
  sensors_snow_depth: null | string;
  sensors_normal_incidence_pyrheliometer: null | string;
  sensors_rain: null | string;
  sensors_temperature: null | string;
  sensors_irradiance: null | string;
  temperature_sensors_ambient_temperature: null | string;
  temperature_sensors_panel_temperature1: null | string;
  temperature_sensors_panel_temperature2: null | string;
  temperature_sensors_min_temperature: null | string;
  temperature_sensors_max_temperature: null | string;
  pyranometer_sensors_reference: null | string;
  pyranometer_sensors_azimuth_and_tilt: null | string;
  pyranometer_sensors_azimuth: null | string;
  pyranometer_sensors_tilt: null | string;
  pyranometer_sensors_tracking: null | string;
  pyranometer_sensors_pyranometer: null | string;
  monthly_insolation_january: null | string;
  monthly_insolation_february: null | string;
  monthly_insolation_march: null | string;
  monthly_insolation_april: null | string;
  monthly_insolation_may: null | string;
  monthly_insolation_june: null | string;
  monthly_insolation_july: null | string;
  monthly_insolation_august: null | string;
  monthly_insolation_september: null | string;
  monthly_insolation_october: null | string;
  monthly_insolation_november: null | string;
  monthly_insolation_december: null | string;
  monthly_insolation_insolation_reference: null | string;
  monthly_insolation_interpolate_daily_insolation: null | string;
}

const WeatherStation = React.forwardRef<DeviceTechnicalDetailsFormRef, DeviceTechnicalDetailsFormProps>(
  ({ mode, setMode, siteId, deviceId, technicalDetailsData: technicalDetailData, reflectFormState, category }, ref) => {
    const { communication, sensors, temperature_sensors, pyranometer_sensors, monthly_insolation } =
      technicalDetailData as WeatherStationTechnicalDetails;

    const queryClient = useQueryClient();
    const notify = useNotify();

    const { handleSubmit, formState, control, reset } = useForm<WeatherStationFormFields>({
      mode: 'onChange',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        ip_address: communication.ip_address,
        port: communication.port !== null ? intFormatter.format(communication.port) : communication.port,
        serial_mode: communication.serial_mode,
        baud: communication.baud !== null ? intFormatter.format(communication.baud) : communication.baud,
        sensors_wind: sensors.wind,
        sensors_humidity: sensors.humidity,
        sensors_barometer: sensors.barometer,
        sensors_snow_depth: sensors.snow_depth,
        sensors_normal_incidence_pyrheliometer: sensors.normal_incidence_pyrheliometer,
        sensors_rain: sensors.rain,
        sensors_temperature: sensors.temperature,
        sensors_irradiance: sensors.irradiance,
        temperature_sensors_ambient_temperature: temperature_sensors.ambient_temperature,
        temperature_sensors_panel_temperature1: temperature_sensors.panel_temperature1,
        temperature_sensors_panel_temperature2: temperature_sensors.panel_temperature2,
        temperature_sensors_min_temperature:
          temperature_sensors.min_temperature !== null
            ? temperature_sensors.min_temperature.toFixed(0)
            : temperature_sensors.min_temperature,
        temperature_sensors_max_temperature:
          temperature_sensors.max_temperature !== null
            ? temperature_sensors.max_temperature.toFixed(0)
            : temperature_sensors.max_temperature,
        pyranometer_sensors_reference: pyranometer_sensors.reference,
        pyranometer_sensors_azimuth_and_tilt: pyranometer_sensors.azimuth_and_tilt,
        pyranometer_sensors_azimuth:
          pyranometer_sensors.azimuth !== null
            ? floatFormatter.format(pyranometer_sensors.azimuth)
            : pyranometer_sensors.azimuth,
        pyranometer_sensors_tilt:
          pyranometer_sensors.tilt !== null
            ? floatFormatter.format(pyranometer_sensors.tilt)
            : pyranometer_sensors.tilt,
        pyranometer_sensors_tracking: pyranometer_sensors.tracking,
        pyranometer_sensors_pyranometer: pyranometer_sensors.pyranometer,
        monthly_insolation_january:
          monthly_insolation.january !== null
            ? formatFloatValue(monthly_insolation.january, true)
            : monthly_insolation.january,
        monthly_insolation_february:
          monthly_insolation.february !== null
            ? formatFloatValue(monthly_insolation.february, true)
            : monthly_insolation.february,
        monthly_insolation_march:
          monthly_insolation.march !== null
            ? formatFloatValue(monthly_insolation.march, true)
            : monthly_insolation.march,
        monthly_insolation_april:
          monthly_insolation.april !== null
            ? formatFloatValue(monthly_insolation.april, true)
            : monthly_insolation.april,
        monthly_insolation_may:
          monthly_insolation.may !== null ? formatFloatValue(monthly_insolation.may, true) : monthly_insolation.may,
        monthly_insolation_june:
          monthly_insolation.june !== null ? formatFloatValue(monthly_insolation.june, true) : monthly_insolation.june,
        monthly_insolation_july:
          monthly_insolation.july !== null ? formatFloatValue(monthly_insolation.july, true) : monthly_insolation.july,
        monthly_insolation_august:
          monthly_insolation.august !== null
            ? formatFloatValue(monthly_insolation.august, true)
            : monthly_insolation.august,
        monthly_insolation_september:
          monthly_insolation.september !== null
            ? formatFloatValue(monthly_insolation.september, true)
            : monthly_insolation.september,
        monthly_insolation_october:
          monthly_insolation.october !== null
            ? formatFloatValue(monthly_insolation.october, true)
            : monthly_insolation.october,
        monthly_insolation_november:
          monthly_insolation.november !== null
            ? formatFloatValue(monthly_insolation.november, true)
            : monthly_insolation.november,
        monthly_insolation_december:
          monthly_insolation.december !== null
            ? formatFloatValue(monthly_insolation.december, true)
            : monthly_insolation.december,
        monthly_insolation_insolation_reference: monthly_insolation.insolation_reference,
        monthly_insolation_interpolate_daily_insolation: monthly_insolation.interpolate_daily_insolation
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateDeviceTechnicalDetails } = useMutation({
      mutationFn: (attributes: WeatherStationTechnicalDetails) => {
        const data: TechnicalDetailAttributes = {
          category,
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
        ip_address: communication.ip_address,
        port: communication.port !== null ? intFormatter.format(communication.port) : communication.port,
        serial_mode: communication.serial_mode,
        baud: communication.baud !== null ? intFormatter.format(communication.baud) : communication.baud,
        sensors_wind: sensors.wind,
        sensors_humidity: sensors.humidity,
        sensors_barometer: sensors.barometer,
        sensors_snow_depth: sensors.snow_depth,
        sensors_normal_incidence_pyrheliometer: sensors.normal_incidence_pyrheliometer,
        sensors_rain: sensors.rain,
        sensors_temperature: sensors.temperature,
        sensors_irradiance: sensors.irradiance,
        temperature_sensors_ambient_temperature: temperature_sensors.ambient_temperature,
        temperature_sensors_panel_temperature1: temperature_sensors.panel_temperature1,
        temperature_sensors_panel_temperature2: temperature_sensors.panel_temperature2,
        temperature_sensors_min_temperature:
          temperature_sensors.min_temperature !== null
            ? temperature_sensors.min_temperature.toFixed(0)
            : temperature_sensors.min_temperature,
        temperature_sensors_max_temperature:
          temperature_sensors.max_temperature !== null
            ? temperature_sensors.max_temperature.toFixed(0)
            : temperature_sensors.max_temperature,
        pyranometer_sensors_reference: pyranometer_sensors.reference,
        pyranometer_sensors_azimuth_and_tilt: pyranometer_sensors.azimuth_and_tilt,
        pyranometer_sensors_azimuth:
          pyranometer_sensors.azimuth !== null
            ? floatFormatter.format(pyranometer_sensors.azimuth)
            : pyranometer_sensors.azimuth,
        pyranometer_sensors_tilt:
          pyranometer_sensors.tilt !== null
            ? floatFormatter.format(pyranometer_sensors.tilt)
            : pyranometer_sensors.tilt,
        pyranometer_sensors_tracking: pyranometer_sensors.tracking,
        pyranometer_sensors_pyranometer: pyranometer_sensors.pyranometer,
        monthly_insolation_january:
          monthly_insolation.january !== null
            ? formatFloatValue(monthly_insolation.january, true)
            : monthly_insolation.january,
        monthly_insolation_february:
          monthly_insolation.february !== null
            ? formatFloatValue(monthly_insolation.february, true)
            : monthly_insolation.february,
        monthly_insolation_march:
          monthly_insolation.march !== null
            ? formatFloatValue(monthly_insolation.march, true)
            : monthly_insolation.march,
        monthly_insolation_april:
          monthly_insolation.april !== null
            ? formatFloatValue(monthly_insolation.april, true)
            : monthly_insolation.april,
        monthly_insolation_may:
          monthly_insolation.may !== null ? formatFloatValue(monthly_insolation.may, true) : monthly_insolation.may,
        monthly_insolation_june:
          monthly_insolation.june !== null ? formatFloatValue(monthly_insolation.june, true) : monthly_insolation.june,
        monthly_insolation_july:
          monthly_insolation.july !== null ? formatFloatValue(monthly_insolation.july, true) : monthly_insolation.july,
        monthly_insolation_august:
          monthly_insolation.august !== null
            ? formatFloatValue(monthly_insolation.august, true)
            : monthly_insolation.august,
        monthly_insolation_september:
          monthly_insolation.september !== null
            ? formatFloatValue(monthly_insolation.september, true)
            : monthly_insolation.september,
        monthly_insolation_october:
          monthly_insolation.october !== null
            ? formatFloatValue(monthly_insolation.october, true)
            : monthly_insolation.october,
        monthly_insolation_november:
          monthly_insolation.november !== null
            ? formatFloatValue(monthly_insolation.november, true)
            : monthly_insolation.november,
        monthly_insolation_december:
          monthly_insolation.december !== null
            ? formatFloatValue(monthly_insolation.december, true)
            : monthly_insolation.december,
        monthly_insolation_insolation_reference: monthly_insolation.insolation_reference,
        monthly_insolation_interpolate_daily_insolation: monthly_insolation.interpolate_daily_insolation
      });
    }, [communication, sensors, monthly_insolation, pyranometer_sensors, temperature_sensors, reset]);

    const onSubmit: SubmitHandler<WeatherStationFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateDeviceTechnicalDetails({
            communication: {
              ip_address: data.ip_address,
              port: data.port !== null ? Number.parseInt(data.port) : null,
              serial_mode: data.serial_mode,
              baud: data.baud !== null ? Number.parseInt(data.baud) : null
            },
            sensors: {
              wind: data.sensors_wind,
              humidity: data.sensors_humidity,
              barometer: data.sensors_barometer,
              snow_depth: data.sensors_snow_depth,
              normal_incidence_pyrheliometer: data.sensors_normal_incidence_pyrheliometer,
              rain: data.sensors_rain,
              temperature: data.sensors_temperature,
              irradiance: data.sensors_irradiance
            },
            temperature_sensors: {
              ambient_temperature: data.temperature_sensors_ambient_temperature,
              panel_temperature1: data.temperature_sensors_panel_temperature1,
              panel_temperature2: data.temperature_sensors_panel_temperature2,
              min_temperature:
                data.temperature_sensors_min_temperature !== null
                  ? Number.parseInt(data.temperature_sensors_min_temperature.replaceAll('+', ''))
                  : data.temperature_sensors_min_temperature,
              max_temperature:
                data.temperature_sensors_max_temperature !== null
                  ? Number.parseInt(data.temperature_sensors_max_temperature.replaceAll('+', ''))
                  : data.temperature_sensors_max_temperature
            },
            pyranometer_sensors: {
              reference: data.pyranometer_sensors_reference,
              azimuth_and_tilt: data.pyranometer_sensors_azimuth_and_tilt,
              azimuth:
                data.pyranometer_sensors_azimuth !== null
                  ? Number.parseFloat(data.pyranometer_sensors_azimuth.replaceAll(',', ''))
                  : data.pyranometer_sensors_azimuth,
              tilt:
                data.pyranometer_sensors_tilt !== null
                  ? Number.parseFloat(data.pyranometer_sensors_tilt.replaceAll(',', ''))
                  : data.pyranometer_sensors_tilt,
              tracking: data.pyranometer_sensors_tracking,
              pyranometer: data.pyranometer_sensors_pyranometer
            },
            monthly_insolation: {
              january:
                data.monthly_insolation_january !== null
                  ? Number.parseFloat(data.monthly_insolation_january.replaceAll(',', ''))
                  : data.monthly_insolation_january,
              february:
                data.monthly_insolation_february !== null
                  ? Number.parseFloat(data.monthly_insolation_february.replaceAll(',', ''))
                  : data.monthly_insolation_february,
              march:
                data.monthly_insolation_march !== null
                  ? Number.parseFloat(data.monthly_insolation_march.replaceAll(',', ''))
                  : data.monthly_insolation_march,
              april:
                data.monthly_insolation_april !== null
                  ? Number.parseFloat(data.monthly_insolation_april.replaceAll(',', ''))
                  : data.monthly_insolation_april,
              may:
                data.monthly_insolation_may !== null
                  ? Number.parseFloat(data.monthly_insolation_may.replaceAll(',', ''))
                  : data.monthly_insolation_may,
              june:
                data.monthly_insolation_june !== null
                  ? Number.parseFloat(data.monthly_insolation_june.replaceAll(',', ''))
                  : data.monthly_insolation_june,
              july:
                data.monthly_insolation_july !== null
                  ? Number.parseFloat(data.monthly_insolation_july.replaceAll(',', ''))
                  : data.monthly_insolation_july,
              august:
                data.monthly_insolation_august !== null
                  ? Number.parseFloat(data.monthly_insolation_august.replaceAll(',', ''))
                  : data.monthly_insolation_august,
              september:
                data.monthly_insolation_september !== null
                  ? Number.parseFloat(data.monthly_insolation_september.replaceAll(',', ''))
                  : data.monthly_insolation_september,
              october:
                data.monthly_insolation_october !== null
                  ? Number.parseFloat(data.monthly_insolation_october.replaceAll(',', ''))
                  : data.monthly_insolation_october,
              november:
                data.monthly_insolation_november !== null
                  ? Number.parseFloat(data.monthly_insolation_november.replaceAll(',', ''))
                  : data.monthly_insolation_november,
              december:
                data.monthly_insolation_december !== null
                  ? Number.parseFloat(data.monthly_insolation_december.replaceAll(',', ''))
                  : data.monthly_insolation_december,
              insolation_reference: data.monthly_insolation_insolation_reference,
              interpolate_daily_insolation: data.monthly_insolation_interpolate_daily_insolation
            }
          });
          notify(response.message || `Technical details were successfully updated.`);
          reset({
            ip_address: data.ip_address,
            port: data.port,
            serial_mode: data.serial_mode,
            baud: data.baud,
            sensors_wind: data.sensors_wind,
            sensors_humidity: data.sensors_humidity,
            sensors_barometer: data.sensors_barometer,
            sensors_snow_depth: data.sensors_snow_depth,
            sensors_normal_incidence_pyrheliometer: data.sensors_normal_incidence_pyrheliometer,
            sensors_rain: data.sensors_rain,
            sensors_temperature: data.sensors_temperature,
            sensors_irradiance: data.sensors_irradiance,
            temperature_sensors_ambient_temperature: data.temperature_sensors_ambient_temperature,
            temperature_sensors_panel_temperature1: data.temperature_sensors_panel_temperature1,
            temperature_sensors_panel_temperature2: data.temperature_sensors_panel_temperature2,
            temperature_sensors_min_temperature: data.temperature_sensors_min_temperature,
            temperature_sensors_max_temperature: data.temperature_sensors_max_temperature,
            pyranometer_sensors_reference: data.pyranometer_sensors_reference,
            pyranometer_sensors_azimuth_and_tilt: data.pyranometer_sensors_azimuth_and_tilt,
            pyranometer_sensors_azimuth: data.pyranometer_sensors_azimuth,
            pyranometer_sensors_tilt: data.pyranometer_sensors_tilt,
            pyranometer_sensors_tracking: data.pyranometer_sensors_tracking,
            pyranometer_sensors_pyranometer: data.pyranometer_sensors_pyranometer,
            monthly_insolation_january: data.monthly_insolation_january,
            monthly_insolation_february: data.monthly_insolation_february,
            monthly_insolation_march: data.monthly_insolation_march,
            monthly_insolation_april: data.monthly_insolation_april,
            monthly_insolation_may: data.monthly_insolation_may,
            monthly_insolation_june: data.monthly_insolation_june,
            monthly_insolation_july: data.monthly_insolation_july,
            monthly_insolation_august: data.monthly_insolation_august,
            monthly_insolation_september: data.monthly_insolation_september,
            monthly_insolation_october: data.monthly_insolation_october,
            monthly_insolation_november: data.monthly_insolation_november,
            monthly_insolation_december: data.monthly_insolation_december,
            monthly_insolation_insolation_reference: data.monthly_insolation_insolation_reference,
            monthly_insolation_interpolate_daily_insolation: data.monthly_insolation_interpolate_daily_insolation
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
                  <TextBox>{communication.ip_address || ''}</TextBox>
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
                  <TextBox>{communication.port !== null ? intFormatter.format(communication.port) : ''}</TextBox>
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
                  <TextBox>{communication.serial_mode || ''}</TextBox>
                ) : (
                  <Controller
                    name="serial_mode"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Serial Mode length should not exceed the limit of 100 characters'
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
                  <TextBox>{communication.baud !== null ? intFormatter.format(communication.baud) : ''}</TextBox>
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
        <SectionTitle variant="h6">Sensors</SectionTitle>
        <SectionTable size="small">
          <TableBody>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Wind</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'edit' ? 'left' : 'right'}>
                {mode === 'view' ? (
                  <TextBox>{sensors.wind || ''}</TextBox>
                ) : (
                  <Controller
                    name="sensors_wind"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.sensors_wind}
                        helperText={errors.sensors_wind?.message}
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
                <TextBox fieldName>Humidity</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'edit' ? 'left' : 'right'}>
                {mode === 'view' ? (
                  <TextBox>{sensors.humidity || ''}</TextBox>
                ) : (
                  <Controller
                    name="sensors_humidity"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.sensors_humidity}
                        helperText={errors.sensors_humidity?.message}
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
                <TextBox fieldName>Barometer</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'edit' ? 'left' : 'right'}>
                {mode === 'view' ? (
                  <TextBox>{sensors.barometer || ''}</TextBox>
                ) : (
                  <Controller
                    name="sensors_barometer"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.sensors_barometer}
                        helperText={errors.sensors_barometer?.message}
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
                <TextBox fieldName>Snow Depth</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'edit' ? 'left' : 'right'}>
                {mode === 'view' ? (
                  <TextBox>{sensors.snow_depth || ''}</TextBox>
                ) : (
                  <Controller
                    name="sensors_snow_depth"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.sensors_snow_depth}
                        helperText={errors.sensors_snow_depth?.message}
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
                <TextBox fieldName>Normal Incidence Pyrheliometer</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'edit' ? 'left' : 'right'}>
                {mode === 'view' ? (
                  <TextBox>{sensors.normal_incidence_pyrheliometer || ''}</TextBox>
                ) : (
                  <Controller
                    name="sensors_normal_incidence_pyrheliometer"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.sensors_normal_incidence_pyrheliometer}
                        helperText={errors.sensors_normal_incidence_pyrheliometer?.message}
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
                <TextBox fieldName>Rain</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'edit' ? 'left' : 'right'}>
                {mode === 'view' ? (
                  <TextBox>{sensors.rain || ''}</TextBox>
                ) : (
                  <Controller
                    name="sensors_rain"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.sensors_rain}
                        helperText={errors.sensors_rain?.message}
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
                <TextBox fieldName>Temperature</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'edit' ? 'left' : 'right'}>
                {mode === 'view' ? (
                  <TextBox>{sensors.temperature || ''}</TextBox>
                ) : (
                  <Controller
                    name="sensors_temperature"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.sensors_temperature}
                        helperText={errors.sensors_temperature?.message}
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
                <TextBox fieldName>Irradiance</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'edit' ? 'left' : 'right'}>
                {mode === 'view' ? (
                  <TextBox>{sensors.irradiance || ''}</TextBox>
                ) : (
                  <Controller
                    name="sensors_irradiance"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.sensors_irradiance}
                        helperText={errors.sensors_irradiance?.message}
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
        <SectionTitle variant="h6">Temperature Sensors</SectionTitle>
        <SectionTable size="small">
          <TableBody>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Ambient Temperature</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'edit' ? 'left' : 'right'}>
                {mode === 'view' ? (
                  <TextBox>{temperature_sensors.ambient_temperature || ''}</TextBox>
                ) : (
                  <Controller
                    name="temperature_sensors_ambient_temperature"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.temperature_sensors_ambient_temperature}
                        helperText={errors.temperature_sensors_ambient_temperature?.message}
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
                <TextBox fieldName>Panel Temperature 1</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'edit' ? 'left' : 'right'}>
                {mode === 'view' ? (
                  <TextBox>{temperature_sensors.panel_temperature1 || ''}</TextBox>
                ) : (
                  <Controller
                    name="temperature_sensors_panel_temperature1"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.temperature_sensors_panel_temperature1}
                        helperText={errors.temperature_sensors_panel_temperature1?.message}
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
                <TextBox fieldName>Panel Temperature 2</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'edit' ? 'left' : 'right'}>
                {mode === 'view' ? (
                  <TextBox>{temperature_sensors.panel_temperature2 || ''}</TextBox>
                ) : (
                  <Controller
                    name="temperature_sensors_panel_temperature2"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.temperature_sensors_panel_temperature2}
                        helperText={errors.temperature_sensors_panel_temperature2?.message}
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
                <TextBox fieldName>Minimum Temperature, &deg;F</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {temperature_sensors.min_temperature !== null
                      ? temparatureFormatter.format(temperature_sensors.min_temperature)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="temperature_sensors_min_temperature"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        return Number.isNaN(Number.parseInt(value))
                          ? 'Invalid number provided as a value for Minimum Temperature'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.temperature_sensors_min_temperature}
                        helperText={errors.temperature_sensors_min_temperature?.message}
                        disabled={isSubmitting}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          inputComponent: FormattedIntegerNegativeAllowedNumericInput as any,
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
                <TextBox fieldName>Maximum Temperature, &deg;F</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {temperature_sensors.max_temperature !== null
                      ? temparatureFormatter.format(temperature_sensors.max_temperature)
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="temperature_sensors_max_temperature"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        return Number.isNaN(Number.parseInt(value))
                          ? 'Invalid number provided as a value for Minimum Temperature'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.temperature_sensors_max_temperature}
                        helperText={errors.temperature_sensors_max_temperature?.message}
                        disabled={isSubmitting}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          inputComponent: FormattedIntegerNegativeAllowedNumericInput as any,
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
        <SectionTitle variant="h6">Pyranometer Sensors</SectionTitle>
        <SectionTable size="small">
          <TableBody>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Reference Pyranometer (GHI)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'edit' ? 'left' : 'right'}>
                {mode === 'view' ? (
                  <TextBox>{pyranometer_sensors.reference || ''}</TextBox>
                ) : (
                  <Controller
                    name="pyranometer_sensors_reference"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.pyranometer_sensors_reference}
                        helperText={errors.pyranometer_sensors_reference?.message}
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
                <TextBox fieldName>Pyranometer (Azimuth & Tilt)</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'edit' ? 'left' : 'right'}>
                {mode === 'view' ? (
                  <TextBox>{pyranometer_sensors.azimuth_and_tilt || ''}</TextBox>
                ) : (
                  <Controller
                    name="pyranometer_sensors_azimuth_and_tilt"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.pyranometer_sensors_azimuth_and_tilt}
                        helperText={errors.pyranometer_sensors_azimuth_and_tilt?.message}
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
                <TextBox fieldName>Pyranometer Azimuth</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {pyranometer_sensors.azimuth !== null ? floatFormatter.format(pyranometer_sensors.azimuth) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="pyranometer_sensors_azimuth"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Pyranometer Azimuth'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.pyranometer_sensors_azimuth}
                        helperText={errors.pyranometer_sensors_azimuth?.message}
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
                <TextBox fieldName>Pyranometer Tilt</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {pyranometer_sensors.tilt !== null ? floatFormatter.format(pyranometer_sensors.tilt) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="pyranometer_sensors_tilt"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Pyranometer Tilt'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.pyranometer_sensors_tilt}
                        helperText={errors.pyranometer_sensors_tilt?.message}
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
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{pyranometer_sensors.tracking || ''}</TextBox>
                ) : (
                  <Controller
                    name="pyranometer_sensors_tracking"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Tracking length should not exceed the limit of 100 characters'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.pyranometer_sensors_tracking}
                        helperText={errors.pyranometer_sensors_tracking?.message}
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
                <TextBox fieldName>Pyranometer</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{pyranometer_sensors.pyranometer || ''}</TextBox>
                ) : (
                  <Controller
                    name="pyranometer_sensors_pyranometer"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Pyranometer length should not exceed the limit of 100 characters'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.pyranometer_sensors_pyranometer}
                        helperText={errors.pyranometer_sensors_pyranometer?.message}
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
        <SectionTitle variant="h6">Monthly Insolation (kWh/m&sup2;)</SectionTitle>
        <SectionTable size="small">
          <TableBody>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>January</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {monthly_insolation.january !== null ? formatFloatValue(monthly_insolation.january) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="monthly_insolation_january"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for January'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.monthly_insolation_january}
                        helperText={errors.monthly_insolation_january?.message}
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
                <TextBox fieldName>February</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {monthly_insolation.february !== null ? formatFloatValue(monthly_insolation.february) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="monthly_insolation_february"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for February'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.monthly_insolation_february}
                        helperText={errors.monthly_insolation_february?.message}
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
                <TextBox fieldName>March</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {monthly_insolation.march !== null ? formatFloatValue(monthly_insolation.march) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="monthly_insolation_march"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for March'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.monthly_insolation_march}
                        helperText={errors.monthly_insolation_march?.message}
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
                <TextBox fieldName>April</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {monthly_insolation.april !== null ? formatFloatValue(monthly_insolation.april) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="monthly_insolation_april"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for April'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.monthly_insolation_april}
                        helperText={errors.monthly_insolation_april?.message}
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
                <TextBox fieldName>May</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{monthly_insolation.may !== null ? formatFloatValue(monthly_insolation.may) : ''}</TextBox>
                ) : (
                  <Controller
                    name="monthly_insolation_may"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for May'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.monthly_insolation_may}
                        helperText={errors.monthly_insolation_may?.message}
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
                <TextBox fieldName>June</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{monthly_insolation.june !== null ? formatFloatValue(monthly_insolation.june) : ''}</TextBox>
                ) : (
                  <Controller
                    name="monthly_insolation_june"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for June'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.monthly_insolation_june}
                        helperText={errors.monthly_insolation_june?.message}
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
                <TextBox fieldName>July</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{monthly_insolation.july !== null ? formatFloatValue(monthly_insolation.july) : ''}</TextBox>
                ) : (
                  <Controller
                    name="monthly_insolation_july"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for July'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.monthly_insolation_july}
                        helperText={errors.monthly_insolation_july?.message}
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
                <TextBox fieldName>August</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {monthly_insolation.august !== null ? formatFloatValue(monthly_insolation.august) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="monthly_insolation_august"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for August'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.monthly_insolation_august}
                        helperText={errors.monthly_insolation_august?.message}
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
                <TextBox fieldName>September</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {monthly_insolation.september !== null ? formatFloatValue(monthly_insolation.september) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="monthly_insolation_september"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for September'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.monthly_insolation_september}
                        helperText={errors.monthly_insolation_september?.message}
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
                <TextBox fieldName>October</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {monthly_insolation.october !== null ? formatFloatValue(monthly_insolation.october) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="monthly_insolation_october"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for October'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.monthly_insolation_october}
                        helperText={errors.monthly_insolation_october?.message}
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
                <TextBox fieldName>November</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {monthly_insolation.november !== null ? formatFloatValue(monthly_insolation.november) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="monthly_insolation_november"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for November'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.monthly_insolation_november}
                        helperText={errors.monthly_insolation_november?.message}
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
                <TextBox fieldName>December</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {monthly_insolation.december !== null ? formatFloatValue(monthly_insolation.december) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="monthly_insolation_december"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for December'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.monthly_insolation_december}
                        helperText={errors.monthly_insolation_december?.message}
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
                <TextBox fieldName>Insolation Reference</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{monthly_insolation.insolation_reference || ''}</TextBox>
                ) : (
                  <Controller
                    name="monthly_insolation_insolation_reference"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Insolation Reference length should not exceed the limit of 100 characters'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.monthly_insolation_insolation_reference}
                        helperText={errors.monthly_insolation_insolation_reference?.message}
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
                <TextBox fieldName>Interpolate Daily Insolation</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'edit' ? 'left' : 'right'}>
                {mode === 'view' ? (
                  <TextBox>{monthly_insolation.interpolate_daily_insolation || ''}</TextBox>
                ) : (
                  <Controller
                    name="monthly_insolation_interpolate_daily_insolation"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Interpolate Daily Insolation length should not exceed the limit of 100 characters'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.monthly_insolation_interpolate_daily_insolation}
                        helperText={errors.monthly_insolation_interpolate_daily_insolation?.message}
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

WeatherStation.displayName = 'Meter';

export default WeatherStation;

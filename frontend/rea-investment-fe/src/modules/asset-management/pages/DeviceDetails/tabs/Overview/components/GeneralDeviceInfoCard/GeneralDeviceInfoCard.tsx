import React from 'react';
import dayjs, { Dayjs } from 'dayjs';
import { AxiosError } from 'axios';
import CustomParseFormatPlugin from 'dayjs/plugin/customParseFormat';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import IconButton from '@mui/material/IconButton';
import EditIcon from '@mui/icons-material/Edit';
import TextField from '@mui/material/TextField';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Fade from '@mui/material/Fade';
import Zoom from '@mui/material/Zoom';
import Divider from '@mui/material/Divider';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import HourglassBottomRoundedIcon from '@mui/icons-material/HourglassBottomRounded';

import { useNotify } from '../../../../../../../../contexts/notifications/notifications';
import { ApiClient, DeviceDetailedInfo } from '../../../../../../../../api';
import {
  DeviceCategory,
  DeviceManufacturersMap,
  DeviceTypesMap
} from '../../../../../../../../components/forms/DeviceForm/constants';

import { FieldCell, StyledSelectItem, TextBox, DetailsContainer } from './GeneralDeviceInfoCard.styles';

dayjs.extend(CustomParseFormatPlugin);

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

type UpdateDeviceGeneralInfo = typeof ApiClient.assetManagement.updateDeviceGeneralInfo;
type UpdateDeviceGeneralInfoAttributes = Parameters<UpdateDeviceGeneralInfo>[number]['attributes'];
type GeneralDeviceInfo = DeviceDetailedInfo['general_info'];

interface TelemetryDeviceMapping {
  telemetry_device_id: string | null;
  telemetry_device_name: string | null;
}

type TelemetrySiteDevicesQueryFunc = typeof ApiClient.assetManagement.telemetrySiteDevices;
type TelemetrySiteDevice = Exclude<Awaited<ReturnType<TelemetrySiteDevicesQueryFunc>>['items'], null>[number];

interface GeneralDeviceInfoCardProps {
  deviceGeneralInfo: GeneralDeviceInfo;
  telemetryMapping: TelemetryDeviceMapping | null;
  deviceId: number;
  siteId: number;
}

interface GeneralDeviceInfoFormFields {
  asset_id: string;
  status: 'Available Inventory' | 'Decommissioned' | 'Placed in Service' | 'RMA';
  name: string;
  category: string;
  type: string | null;
  manufacturer: string | null;
  model: string;
  serial_number: string;
  telemetry_device?: TelemetrySiteDevice;
  warranty_effective_date?: Dayjs | null;
  warranty_term?: string | null;
  gateway_id?: string | null;
  function_id?: string | null;
  driver?: string | null;
  install_date?: Dayjs | null;
  decommissioned_date?: Dayjs | null;
  last_updated_date?: Dayjs | null;
  das_connection_status?: string | null;
}

export const GeneralDeviceInfoCard: React.FC<GeneralDeviceInfoCardProps> = ({
  deviceGeneralInfo,
  telemetryMapping,
  deviceId,
  siteId
}) => {
  const [mode, setMode] = React.useState<'view' | 'edit'>('view');

  const queryClient = useQueryClient();
  const notify = useNotify();

  const { mutateAsync: updateDeviceGeneralInfo } = useMutation({
    mutationFn: (attributes: UpdateDeviceGeneralInfoAttributes) =>
      ApiClient.assetManagement.updateDeviceGeneralInfo({
        siteId,
        deviceId,
        attributes
      })
  });

  const { mutateAsync: updateDevices } = useMutation({
    mutationFn: async ({ siteId, deviceId }: { siteId: number; deviceId: number }) => {
      return ApiClient.assetManagement.updateTelemetrySiteDevices(siteId, deviceId);
    }
  });

  const {
    data: telemetrySiteDevicesResponse,
    error: errorRetrievingTelemetrySiteDevices,
    isLoading: isLoadingTelemetrySiteDevices
  } = useQuery({
    queryFn: () => ApiClient.assetManagement.telemetrySiteDevices(siteId),
    queryKey: ['telemetry-devices', { siteId }],
    enabled: mode === 'edit'
  });

  const { handleSubmit, formState, control, reset, setValue } = useForm<GeneralDeviceInfoFormFields>({
    mode: 'onChange',
    criteriaMode: 'all',
    reValidateMode: 'onChange',
    defaultValues: {
      asset_id: deviceGeneralInfo.asset_id,
      status: deviceGeneralInfo.status,
      name: deviceGeneralInfo.name,
      category: deviceGeneralInfo.category,
      type: deviceGeneralInfo.type,
      manufacturer: deviceGeneralInfo.manufacturer,
      model: deviceGeneralInfo.model,
      serial_number: deviceGeneralInfo.serial_number,
      warranty_effective_date: deviceGeneralInfo.warranty_effective_date
        ? dayjs(deviceGeneralInfo.warranty_effective_date, 'YYYY-MM-DD', true)
        : null,
      warranty_term: deviceGeneralInfo.warranty_term,
      gateway_id: deviceGeneralInfo.gateway_id,
      function_id: deviceGeneralInfo.function_id,
      driver: deviceGeneralInfo.driver,
      install_date: deviceGeneralInfo.install_date ? dayjs(deviceGeneralInfo.install_date, 'YYYY-MM-DD', true) : null,
      decommissioned_date: deviceGeneralInfo.decommissioned_date
        ? dayjs(deviceGeneralInfo.decommissioned_date, 'YYYY-MM-DD', true)
        : null,
      last_updated_date: deviceGeneralInfo.last_updated_date
        ? dayjs(deviceGeneralInfo.last_updated_date, 'YYYY-MM-DD', true)
        : null,
      ...(telemetryMapping && {
        telemetry_device:
          telemetryMapping.telemetry_device_id && telemetryMapping.telemetry_device_name
            ? { name: telemetryMapping.telemetry_device_name, id: telemetryMapping.telemetry_device_id }
            : { name: undefined, id: undefined }
      })
    }
  });

  const { errors, isValid, isSubmitting, isDirty, dirtyFields } = formState;

  React.useEffect(() => {
    reset({
      asset_id: deviceGeneralInfo.asset_id,
      status: deviceGeneralInfo.status,
      name: deviceGeneralInfo.name,
      category: deviceGeneralInfo.category,
      type: deviceGeneralInfo.type,
      manufacturer: deviceGeneralInfo.manufacturer,
      model: deviceGeneralInfo.model,
      serial_number: deviceGeneralInfo.serial_number,
      warranty_effective_date: deviceGeneralInfo.warranty_effective_date
        ? dayjs(deviceGeneralInfo.warranty_effective_date, 'YYYY-MM-DD', true)
        : null,
      warranty_term: deviceGeneralInfo.warranty_term,
      gateway_id: deviceGeneralInfo.gateway_id,
      function_id: deviceGeneralInfo.function_id,
      driver: deviceGeneralInfo.driver,
      install_date: deviceGeneralInfo.install_date ? dayjs(deviceGeneralInfo.install_date, 'YYYY-MM-DD', true) : null,
      decommissioned_date: deviceGeneralInfo.decommissioned_date
        ? dayjs(deviceGeneralInfo.decommissioned_date, 'YYYY-MM-DD', true)
        : null,
      last_updated_date: deviceGeneralInfo.last_updated_date
        ? dayjs(deviceGeneralInfo.last_updated_date, 'YYYY-MM-DD', true)
        : null,
      ...(telemetryMapping && {
        telemetry_device:
          telemetryMapping.telemetry_device_id && telemetryMapping.telemetry_device_name
            ? { name: telemetryMapping.telemetry_device_name, id: telemetryMapping.telemetry_device_id }
            : { name: undefined, id: undefined }
      })
    });
  }, [deviceGeneralInfo, telemetryMapping, reset]);

  const onSubmit: SubmitHandler<GeneralDeviceInfoFormFields> = async data => {
    try {
      const response = await updateDeviceGeneralInfo({
        asset_id: data.asset_id,
        status: data.status,
        name: data.name,
        type: data.type,
        manufacturer: data.manufacturer,
        model: data.model,
        serial_number: data.serial_number,
        warranty_effective_date: data.warranty_effective_date
          ? data.warranty_effective_date.format('YYYY-MM-DD')
          : null,
        warranty_term: data.warranty_term ?? null,
        gateway_id: data.gateway_id ?? null,
        function_id: data.function_id ?? null,
        driver: data.driver ?? null,
        install_date: data.install_date ? data.install_date.format('YYYY-MM-DD') : null,
        decommissioned_date: data.decommissioned_date ? data.decommissioned_date.format('YYYY-MM-DD') : null,
        last_updated_date: data.last_updated_date ? data.last_updated_date.format('YYYY-MM-DD') : null,
        ...(data.telemetry_device &&
          dirtyFields.telemetry_device && {
            telemetry_device_id: data.telemetry_device.id === 'none' ? null : data.telemetry_device.id,
            telemetry_device_name: data.telemetry_device.id === 'none' ? null : data.telemetry_device.name
          })
      });

      if (dirtyFields.telemetry_device && response?.code === 202) {
        try {
          await updateDevices({ siteId, deviceId });
          notify('The device data has been successfully retrieved from DAS');
        } catch (e: any) {
          notify('We encountered an issue while retrieving the device data. Please fill in the information manually');
        }
      }

      notify(response.message || `General device info was successfully updated.`);
      reset({
        asset_id: data.asset_id,
        status: data.status,
        name: data.name,
        type: data.type,
        category: data.category,
        manufacturer: data.manufacturer,
        model: data.model,
        serial_number: data.serial_number,
        warranty_effective_date: data.warranty_effective_date,
        warranty_term: data.warranty_term,
        gateway_id: data.gateway_id,
        function_id: data.function_id,
        driver: data.driver,
        install_date: data.install_date,
        decommissioned_date: data.decommissioned_date,
        last_updated_date: data.last_updated_date,
        ...(data.telemetry_device && {
          telemetry_device: data.telemetry_device
        })
      });
      queryClient.invalidateQueries({ queryKey: ['device'] });
      mode === 'edit' && setMode('view');
    } catch (e: any) {
      notify(e.response?.data?.message || 'Something went wrong when updating the General device info...');
    }
  };

  const handleClickEdit = () => setMode('edit');

  const handleClickCancel = () => {
    reset();
    setMode('view');
  };

  const {
    asset_id,
    status,
    name,
    type,
    manufacturer,
    category,
    model,
    serial_number,
    warranty_effective_date,
    warranty_term,
    gateway_id,
    function_id,
    driver,
    install_date,
    decommissioned_date,
    last_updated_date,
    das_connection_status
  } = deviceGeneralInfo;

  const deviceStatus = React.useMemo(() => deviceGeneralInfo.status, [deviceGeneralInfo]);

  React.useEffect(() => {
    if (deviceStatus === 'Decommissioned' && mode === 'edit') {
      reset();
      setMode('view');
    }
  }, [deviceStatus, mode, reset]);

  const disableTypeSelection = React.useMemo(() => !category || DeviceTypesMap[category] === null, [category]);
  const deviceTypeOptions = React.useMemo(() => {
    const deviceTypes = DeviceTypesMap[category];
    return deviceTypes && deviceTypes.length ? (
      deviceTypes.map(type => (
        <StyledSelectItem key={type} value={type}>
          {type}
        </StyledSelectItem>
      ))
    ) : (
      <StyledSelectItem value="Other">Other</StyledSelectItem>
    );
  }, [category]);

  const disableManufacturerSelection = React.useMemo(
    () => !category || DeviceManufacturersMap[category] === null,
    [category]
  );
  const deviceManufacturerOptions = React.useMemo(() => {
    const deviceManufacturers = DeviceManufacturersMap[category];
    return deviceManufacturers && deviceManufacturers.length ? (
      deviceManufacturers.map(manufacturer => (
        <StyledSelectItem key={manufacturer} value={manufacturer}>
          {manufacturer}
        </StyledSelectItem>
      ))
    ) : (
      <StyledSelectItem value="Other">Other</StyledSelectItem>
    );
  }, [category]);

  const telemetrySiteDevicesOptions: TelemetrySiteDevice[] = [...(telemetrySiteDevicesResponse?.items ?? [])];

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)}>
      <DetailsContainer position="relative" display="flex" flexDirection="column" flexGrow={1}>
        <Stack direction="row" p="8px" pb="16px" flexWrap="nowrap" justifyContent="space-between" alignItems="center">
          <Typography variant="h5" mb="0">
            General Device Information
          </Typography>
          {deviceStatus !== 'Decommissioned' && (
            <Zoom in={mode === 'view'}>
              <Box borderRadius="50%" bgcolor="rgba(255, 255, 255, 0.85)">
                <IconButton
                  data-testid="device_details-general_device_info-edit_btn"
                  size="small"
                  onClick={handleClickEdit}
                >
                  <EditIcon fontSize="small" sx={{ color: '#404251' }} />
                </IconButton>
              </Box>
            </Zoom>
          )}
        </Stack>
        <Box px="8px">
          <Divider sx={{ borderBottom: '1px solid #0000003B', height: '1px', marginBottom: '8px' }} />
        </Box>
        <Table sx={{ width: '100%', height: 'auto', tableLayout: 'fixed' }} size="small">
          <TableBody>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Device Status</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{status}</TextBox>
                ) : (
                  <Controller
                    name="status"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        placeholder=""
                        error={!!errors.status}
                        helperText={errors.status?.message}
                        disabled={isSubmitting}
                        InputProps={{
                          sx: inputStyles
                        }}
                        select
                        fullWidth
                        variant="outlined"
                        size="small"
                      >
                        {['Available Inventory', 'Decommissioned', 'Placed in Service', 'RMA'].map(status => (
                          <StyledSelectItem key={status} value={status}>
                            {status}
                          </StyledSelectItem>
                        ))}
                      </TextField>
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Connection Status:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{das_connection_status}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>{'Device Name' + (mode === 'edit' ? ' *' : '')}</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{name}</TextBox>
                ) : (
                  <Controller
                    name="name"
                    control={control}
                    rules={{
                      required: 'Device Name is required field.',
                      pattern: {
                        value: /^[a-zA-Z0-9\s(){}[\]<>'".,/#!?$%^&*;:=\-+_`~@]*$/,
                        message:
                          'Device Name should contain only alphabetic, numeric and special characters, spaces are allowed.'
                      },
                      minLength: {
                        value: 2,
                        message: 'Device Name length should be between 2 and 100 characters.'
                      },
                      maxLength: {
                        value: 100,
                        message: 'Device Name length should be between 2 and 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.name}
                        helperText={errors.name?.message}
                        multiline
                        required
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{ sx: inputStyles }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Asset ID</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{asset_id}</TextBox>
                ) : (
                  <Controller
                    name="asset_id"
                    control={control}
                    rules={{
                      minLength: {
                        value: 2,
                        message: 'Asset ID length should be between 2 and 100 characters.'
                      },
                      maxLength: {
                        value: 100,
                        message: 'Asset ID length should be between 2 and 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.asset_id}
                        helperText={errors.asset_id?.message}
                        multiline
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{ sx: inputStyles }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>{'Device Category' + (mode === 'edit' ? ' *' : '')}</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{category}</TextBox>
                ) : (
                  <Controller
                    name="category"
                    control={control}
                    rules={{
                      required: 'Device Category is required field'
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        placeholder=""
                        disabled
                        error={!!errors.category}
                        helperText={errors.category?.message}
                        InputProps={{
                          sx: inputStyles
                        }}
                        select
                        required
                        fullWidth
                        variant="outlined"
                        size="small"
                      >
                        {Object.values(DeviceCategory).map(category => (
                          <StyledSelectItem key={category} value={category}>
                            {category}
                          </StyledSelectItem>
                        ))}
                      </TextField>
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Device Type</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{type}</TextBox>
                ) : (
                  <Controller
                    name="type"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        placeholder=""
                        disabled={disableTypeSelection || isSubmitting}
                        error={!!errors.type}
                        helperText={errors.type?.message}
                        InputProps={{
                          sx: inputStyles
                        }}
                        select
                        fullWidth
                        variant="outlined"
                        size="small"
                      >
                        {deviceTypeOptions}
                      </TextField>
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Manufacturer</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{manufacturer}</TextBox>
                ) : (
                  <Controller
                    name="manufacturer"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        placeholder=""
                        disabled={disableManufacturerSelection || isSubmitting}
                        error={!!errors.manufacturer}
                        helperText={errors.manufacturer?.message}
                        InputProps={{
                          sx: inputStyles
                        }}
                        select
                        fullWidth
                        variant="outlined"
                        size="small"
                      >
                        {deviceManufacturerOptions}
                      </TextField>
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Model</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{model}</TextBox>
                ) : (
                  <Controller
                    name="model"
                    control={control}
                    rules={{
                      pattern: {
                        value: /^[a-zA-Z0-9\s]*$/,
                        message: 'Model should contain only alphabetic and numeric characters, spaces are allowed.'
                      },
                      minLength: {
                        value: 2,
                        message: 'Model length should be between 2 and 100 characters.'
                      },
                      maxLength: {
                        value: 100,
                        message: 'Model length should be between 2 and 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.model}
                        helperText={errors.model?.message}
                        multiline
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{ sx: inputStyles }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Serial # / Asset Tag</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{serial_number}</TextBox>
                ) : (
                  <Controller
                    name="serial_number"
                    control={control}
                    rules={{
                      pattern: {
                        value: /^[a-zA-Z0-9-]*$/,
                        message:
                          'Serial # / Asset Tag should contain only alphabetic, numeric and hyphen characters, spaces are not allowed.'
                      },
                      minLength: {
                        value: 2,
                        message: 'Serial # / Asset Tag length should be between 2 and 100 characters.'
                      },
                      maxLength: {
                        value: 100,
                        message: 'Serial # / Asset Tag length should be between 2 and 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.serial_number}
                        helperText={errors.serial_number?.message}
                        multiline
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{ sx: inputStyles }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Device for Mapping</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{telemetryMapping?.telemetry_device_name ?? 'None'}</TextBox>
                ) : (
                  <Controller
                    name="telemetry_device"
                    control={control}
                    render={({ field: { ref, value, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e =>
                          setValue(
                            'telemetry_device',
                            telemetrySiteDevicesOptions.find(device => device.id === e.target.value),
                            { shouldDirty: true, shouldValidate: true }
                          )
                        }
                        value={value?.id || ''}
                        inputRef={ref}
                        placeholder=""
                        error={!!errorRetrievingTelemetrySiteDevices || !!errors.telemetry_device}
                        helperText={
                          errors.telemetry_device?.message ||
                          (errorRetrievingTelemetrySiteDevices instanceof AxiosError
                            ? errorRetrievingTelemetrySiteDevices.response?.data?.message
                            : errorRetrievingTelemetrySiteDevices?.message)
                        }
                        disabled={
                          isSubmitting ||
                          isLoadingTelemetrySiteDevices ||
                          (!dirtyFields.telemetry_device && !!value?.id && value.id !== 'none')
                        }
                        SelectProps={{
                          IconComponent: isLoadingTelemetrySiteDevices ? HourglassBottomRoundedIcon : undefined
                        }}
                        InputProps={{
                          sx: inputStyles
                        }}
                        select
                        fullWidth
                        variant="outlined"
                        size="small"
                      >
                        {telemetrySiteDevicesOptions.map(telemetryDevice => (
                          <StyledSelectItem
                            key={telemetryDevice.name}
                            value={telemetryDevice.id}
                            {...(telemetryDevice.id === 'none' && { sx: { color: '#4F4F4F' } })}
                          >
                            {telemetryDevice.name}
                          </StyledSelectItem>
                        ))}
                      </TextField>
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Warranty Effective Date</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {warranty_effective_date
                      ? dayjs(warranty_effective_date, 'YYYY-MM-DD', true).format('MM/DD/YYYY')
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="warranty_effective_date"
                    control={control}
                    rules={{
                      validate: value => {
                        if (value === null) return true;
                        if (!dayjs(value).isValid()) return 'Please enter correct date';
                        return true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <DatePicker
                        {...field}
                        value={value}
                        format="MM/DD/YYYY"
                        inputRef={ref}
                        onChange={val => onChange(val)}
                        slotProps={{
                          textField: {
                            error: !!errors.warranty_effective_date,
                            helperText: errors.warranty_effective_date?.message,
                            size: 'small',
                            fullWidth: true,
                            InputProps: { sx: inputStyles },
                            variant: 'outlined',
                            disabled: isSubmitting
                          }
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Warranty Term</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{warranty_term}</TextBox>
                ) : (
                  <Controller
                    name="warranty_term"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Warranty Term length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.warranty_term}
                        helperText={errors.warranty_term?.message}
                        multiline
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{ sx: inputStyles }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Gateway ID</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{gateway_id}</TextBox>
                ) : (
                  <Controller
                    name="gateway_id"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Gateway ID length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.gateway_id}
                        helperText={errors.gateway_id?.message}
                        multiline
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{ sx: inputStyles }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Function ID</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{function_id}</TextBox>
                ) : (
                  <Controller
                    name="function_id"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Function ID length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.function_id}
                        helperText={errors.function_id?.message}
                        multiline
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{ sx: inputStyles }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Driver</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{driver}</TextBox>
                ) : (
                  <Controller
                    name="driver"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Driver length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.driver}
                        helperText={errors.driver?.message}
                        multiline
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{ sx: inputStyles }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Install Date</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{install_date ? dayjs(install_date, 'YYYY-MM-DD', true).format('MM/DD/YYYY') : ''}</TextBox>
                ) : (
                  <Controller
                    name="install_date"
                    control={control}
                    rules={{
                      validate: value => {
                        if (value === null) return true;
                        if (!dayjs(value).isValid()) return 'Please enter correct date';
                        return true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <DatePicker
                        {...field}
                        value={value}
                        format="MM/DD/YYYY"
                        inputRef={ref}
                        onChange={val => onChange(val)}
                        slotProps={{
                          textField: {
                            error: !!errors.install_date,
                            helperText: errors.install_date?.message,
                            size: 'small',
                            fullWidth: true,
                            InputProps: { sx: inputStyles },
                            variant: 'outlined',
                            disabled: isSubmitting
                          }
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Decommissioned Date</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {decommissioned_date ? dayjs(decommissioned_date, 'YYYY-MM-DD', true).format('MM/DD/YYYY') : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="decommissioned_date"
                    control={control}
                    rules={{
                      validate: value => {
                        if (value === null) return true;
                        if (!dayjs(value).isValid()) return 'Please enter correct date';
                        return true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <DatePicker
                        {...field}
                        value={value}
                        format="MM/DD/YYYY"
                        inputRef={ref}
                        onChange={val => onChange(val)}
                        slotProps={{
                          textField: {
                            error: !!errors.decommissioned_date,
                            helperText: errors.decommissioned_date?.message,
                            size: 'small',
                            fullWidth: true,
                            InputProps: { sx: inputStyles },
                            variant: 'outlined',
                            disabled: isSubmitting
                          }
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Last Updated</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {last_updated_date ? dayjs(last_updated_date, 'YYYY-MM-DD', true).format('MM/DD/YYYY') : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="last_updated_date"
                    control={control}
                    rules={{
                      validate: value => {
                        if (value === null) return true;
                        if (!dayjs(value).isValid()) return 'Please enter correct date';
                        return true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <DatePicker
                        {...field}
                        value={value}
                        format="MM/DD/YYYY"
                        inputRef={ref}
                        onChange={val => onChange(val)}
                        slotProps={{
                          textField: {
                            error: !!errors.last_updated_date,
                            helperText: errors.last_updated_date?.message,
                            size: 'small',
                            fullWidth: true,
                            InputProps: { sx: inputStyles },
                            variant: 'outlined',
                            disabled: isSubmitting
                          }
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
          </TableBody>
        </Table>
        <Stack
          width="100%"
          direction="row"
          flexWrap="nowrap"
          alignItems="center"
          justifyContent="flex-end"
          px="8px"
          pt="16px"
          pb="8px"
        >
          {mode === 'edit' && (
            <Fade in={mode === 'edit'} timeout={{ enter: 1000, exit: 1000 }}>
              <Stack direction="row" spacing={1}>
                <Button disabled={!isValid || !isDirty || isSubmitting} variant="contained" size="small" type="submit">
                  Save
                </Button>
                <Button disabled={isSubmitting} variant="outlined" size="small" onClick={handleClickCancel}>
                  Cancel
                </Button>
              </Stack>
            </Fade>
          )}
        </Stack>
      </DetailsContainer>
    </Box>
  );
};

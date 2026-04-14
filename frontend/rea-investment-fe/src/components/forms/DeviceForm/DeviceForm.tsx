import * as React from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useForm, SubmitHandler, Controller } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { AxiosError } from 'axios';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import FormHelperText from '@mui/material/FormHelperText';
import TextField from '@mui/material/TextField';
import Alert from '@mui/material/Alert';
import Collapse from '@mui/material/Collapse';
import Typography from '@mui/material/Typography';
import { ApiClient } from '../../../api';
import { useNotify } from '../../../contexts/notifications/notifications';
import { DeviceCategory, DeviceCategoryValue } from './constants';
import { SearchableSelect, SearchableSelectOption } from '../../common/SearchableSelect/SearchableSelect';

const noBottomLineStyles = {
  '& .MuiInputBase-root:not(.Mui-disabled, .Mui-error)': {
    '&::before, &:hover::before, &.Mui-focused::after': {
      borderBottomColor: 'transparent',
      transform: 'scaleX(0)'
    }
  }
};

type AddDeviceParams = Parameters<typeof ApiClient.assetManagement.createDevice>[1];
type TelemetrySiteDevicesQueryFunc = typeof ApiClient.assetManagement.telemetrySiteDevices;

type TelemetrySiteDevice = Exclude<Awaited<ReturnType<TelemetrySiteDevicesQueryFunc>>['items'], null>[number];

type DeviceFormFields = {
  name: string;
  category: DeviceCategoryValue;
  telemetry_device?: TelemetrySiteDevice;
};

type DeviceFormProps = {
  mode: 'add';
  siteId: number;
  companyId: number;
};

const categoryOptions: SearchableSelectOption[] = Object.values(DeviceCategory).map(category => ({
  label: category,
  value: category
}));

export const DeviceForm: React.FC<DeviceFormProps> = ({ siteId, companyId }) => {
  const notify = useNotify();

  const {
    data: telemetrySiteDevicesResponse,
    error: errorRetrievingTelemetrySiteDevices,
    isLoading: isLoadingTelemetrySiteDevices
  } = useQuery({
    queryFn: () => ApiClient.assetManagement.telemetrySiteDevices(siteId),
    queryKey: ['telemetry-devices', { siteId }]
  });

  const { mutateAsync: addDevice } = useMutation({
    mutationFn: (attributes: AddDeviceParams) => ApiClient.assetManagement.createDevice(siteId, attributes)
  });

  const { mutateAsync: updateDevices } = useMutation({
    mutationFn: async ({ siteId, deviceId }: { siteId: number; deviceId: number }) => {
      return ApiClient.assetManagement.updateTelemetrySiteDevices(siteId, deviceId);
    }
  });

  const navigate = useNavigate();

  const { handleSubmit, formState, setError, setValue, control, reset, clearErrors, trigger } =
    useForm<DeviceFormFields>({
      mode: 'onBlur',
      criteriaMode: 'all',
      reValidateMode: 'onBlur',
      defaultValues: {
        name: undefined,
        category: undefined
      }
    });

  const onSubmit: SubmitHandler<DeviceFormFields> = async data => {
    try {
      const message = await addDevice({
        name: data.name,
        category: data.category,
        ...(data.telemetry_device && {
          telemetry_device_id: data.telemetry_device.id === 'none' ? null : data.telemetry_device.id,
          telemetry_device_name: data.telemetry_device.id === 'none' ? null : data.telemetry_device.name
        })
      });
      notify(message?.message || 'Device was added successfully.');
      if (formState?.dirtyFields.telemetry_device && message.device_id && message?.message) {
        try {
          const deviceId = message.device_id;
          await updateDevices({ siteId, deviceId });
          notify('The device data has been successfully retrieved from DAS');
        } catch (e: any) {
          notify('We encountered an issue while retrieving the device data. Please fill in the information manually');
        }
      }
      reset();
      setTimeout(() => navigate(`/project-hub/companies/${companyId}/sites/${siteId}/devices`), 1000);
    } catch (e: any) {
      notify(
        e instanceof AxiosError
          ? e.response?.data?.message || e.message
          : e.message || 'Something went wrong when adding a new device...'
      );
      setError('root', {
        message: e.response?.data?.message || 'Device-entry creation failed'
      });
      setTimeout(() => {
        clearErrors('root');
        trigger();
      }, 5000);
    }
  };

  const { errors, isValid, isSubmitted, isSubmitSuccessful, isSubmitting, isDirty } = formState;

  const handleClickBack = () => navigate(-1);

  const telemetrySiteDevicesOptions: TelemetrySiteDevice[] = [...(telemetrySiteDevicesResponse?.items ?? [])];

  const telemetryDeviceSelectOptions: SearchableSelectOption[] = telemetrySiteDevicesOptions.map(device => ({
    label: device.name,
    value: device.id
  }));

  return (
    <Stack component="form" noValidate width="30%" minWidth="320px" spacing={2} onSubmit={handleSubmit(onSubmit)}>
      <Typography variant="h6">General Details</Typography>
      <Controller
        name="name"
        control={control}
        rules={{
          required: 'Device Name is required field.',
          pattern: {
            value: /^[a-zA-Z0-9\s(){}[\]<>'".,/#!?$%^&*;:=\-+_`~@]*$/,
            message: 'Device Name should contain only alphabetic, numeric and special characters, spaces are allowed.'
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
        render={({ field: { ref, value, ...field } }) => (
          <TextField
            {...field}
            variant="filled"
            required
            label="Device Name"
            sx={noBottomLineStyles}
            helperText={errors.name?.message}
            error={!!errors.name}
            inputRef={ref}
            value={value || ''}
          />
        )}
      />
      <Controller
        name="category"
        control={control}
        rules={{ required: 'Device Category is required field.' }}
        render={({ field }) => (
          <SearchableSelect
            options={categoryOptions}
            value={field.value || null}
            onChange={val => field.onChange(val)}
            onBlur={field.onBlur}
            inputRef={field.ref}
            label="Device Category"
            required
            error={!!errors.category}
            helperText={errors.category?.message}
            variant="filled"
            disabled={field.disabled}
            formControlSx={noBottomLineStyles}
          />
        )}
      />
      <Typography variant="h6" marginTop="24px !important">
        Telemetry
      </Typography>
      <Controller
        name="telemetry_device"
        control={control}
        render={({ field }) => (
          <SearchableSelect
            options={telemetryDeviceSelectOptions}
            value={field.value?.id || null}
            onChange={val => {
              const device = telemetrySiteDevicesOptions.find(d => d.id === val);
              setValue('telemetry_device', device, { shouldDirty: true, shouldValidate: true, shouldTouch: true });
            }}
            onBlur={field.onBlur}
            inputRef={field.ref}
            label="Device for Mapping"
            error={!!errorRetrievingTelemetrySiteDevices || !!errors.telemetry_device}
            helperText={
              errors.telemetry_device?.message ||
              (errorRetrievingTelemetrySiteDevices instanceof AxiosError
                ? errorRetrievingTelemetrySiteDevices.response?.data?.message ||
                  errorRetrievingTelemetrySiteDevices.message
                : errorRetrievingTelemetrySiteDevices?.message ??
                  (errorRetrievingTelemetrySiteDevices
                    ? 'Something went wrong when retrieving telemetry site devices...'
                    : undefined))
            }
            variant="filled"
            disabled={isLoadingTelemetrySiteDevices}
            loading={isLoadingTelemetrySiteDevices}
            formControlSx={noBottomLineStyles}
          />
        )}
      />
      <Stack direction="row" width="100%" spacing={3} justifyContent="stretch" marginTop="24px !important">
        <Button fullWidth variant="outlined" onClick={handleClickBack}>
          Back
        </Button>
        <Button disabled={!isValid || !isDirty || isSubmitting} fullWidth variant="contained" type="submit">
          Add
        </Button>
      </Stack>
      <Collapse in={isSubmitted && !isSubmitSuccessful && !!errors.root}>
        <Alert severity="error">{errors.root?.message}</Alert>
      </Collapse>
    </Stack>
  );
};

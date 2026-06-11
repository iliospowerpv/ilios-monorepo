import React, { useState } from 'react';
import { AxiosError } from 'axios';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm, SubmitHandler, Controller } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';

import formatNumericValue from '../../../utils/formatters/formatFloatValue';
import { State } from '../../../utils/asset-managment';
import { useNotify } from '../../../contexts/notifications/notifications';
import { FormattedNumericInput } from '../../common/FormattedNumericInput/FormattedNumericInput';
import {
  ApiClient,
  Connection,
  CreateSiteAttributes,
  SiteDetailedInfo,
  CreateSiteMappingAttributes,
  SiteMapping
} from '../../../api';
import { SearchableSelect, SearchableSelectOption } from '../../common/SearchableSelect/SearchableSelect';
import { SearchableMultiSelect } from '../../common/SearchableSelect/SearchableMultiSelect';

const noBottomLineStyles = {
  '& .MuiInputBase-root:not(.Mui-disabled, .Mui-error)': {
    '&::before, &:hover::before, &.Mui-focused::after': {
      borderBottomColor: 'transparent',
      transform: 'scaleX(0)'
    }
  }
};

type SiteFormFields = {
  company_id?: number;
  name: string;
  address: string;
  city: string;
  state: string;
  county?: string;
  zip_code: string;
  system_size_ac: string;
  system_size_dc: string;
  das_connection_name: string;
  telemetry_site_name: string;
  lon_lat_url: string;
  cameras_uuids: string[];
  timezone: string;
};

type SiteFormProps =
  | { mode: 'add'; siteId?: number; siteData?: SiteDetailedInfo; companyId: number }
  | { mode: 'edit'; siteId: number; siteData: SiteDetailedInfo; companyId: number };

const stateOptions: SearchableSelectOption[] = Object.entries(State).map(([key, value]) => ({
  label: value,
  value: key
}));

// IANA timezone options for the per-site timezone selector. Prefer the browser's
// full IANA list (Intl.supportedValuesOf); fall back to common US zones + UTC
// when the runtime doesn't support it. The stored value drives site-local
// telemetry/reporting math; app timestamps still render in the viewer's timezone.
const TIMEZONE_FALLBACK = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Phoenix',
  'America/Los_Angeles',
  'America/Anchorage',
  'Pacific/Honolulu'
];

const getTimezoneOptions = (): SearchableSelectOption[] => {
  let zones: string[] = TIMEZONE_FALLBACK;
  try {
    const supported = (
      Intl as unknown as { supportedValuesOf?: (key: string) => string[] }
    ).supportedValuesOf?.('timeZone');
    if (Array.isArray(supported) && supported.length) zones = supported;
  } catch {
    // keep fallback
  }
  return Array.from(new Set(['UTC', ...zones])).map(zone => ({ label: zone, value: zone }));
};

const timezoneOptions: SearchableSelectOption[] = getTimezoneOptions();

export const SiteForm: React.FC<SiteFormProps> = props => {
  const { companyId, siteId, mode, siteData } = props;
  const navigate = useNavigate();
  const notify = useNotify();
  const queryClient = useQueryClient();
  const isEdit = mode === 'edit';
  const [loading, setLoading] = useState(false);
  const [selectedConnection, setSelectedConnection] = useState<Connection | null>(null);
  const [selectedSite, setSelectedSite] = useState<SiteMapping | null>(null);

  const { mutateAsync } = useMutation({
    mutationFn: async (attributes: CreateSiteAttributes) => {
      if (siteId) {
        return await ApiClient.assetManagement.updateSite(siteId, attributes);
      } else {
        return await ApiClient.assetManagement.createSite(attributes);
      }
    }
  });

  const { mutateAsync: saveMappingData } = useMutation({
    mutationFn: async ({ id, attributes }: { id: number | undefined; attributes: CreateSiteMappingAttributes }) => {
      return ApiClient.connections.createSiteMapping(id, attributes);
    }
  });

  const {
    data: connectionData,
    isLoading: isLoadingConnectionData,
    error: connectionError
  } = useQuery({
    queryFn: async () => {
      return ApiClient.connections.getConnections(companyId || -1);
    },
    queryKey: ['connections', { companyId }],
    enabled: !siteData?.telemetry_site_name
  });

  const {
    data: siteMappingData,
    isLoading: isLoadingSitesData,
    error: siteError
  } = useQuery({
    queryFn: async () => {
      return ApiClient.connections.getSites(companyId || -1, selectedConnection?.id || -1);
    },
    queryKey: ['sites', { companyId, connectionId: selectedConnection?.id }],
    enabled: !!selectedConnection?.id
  });

  const {
    data: cameraData,
    isLoading: isLoadingCameraData,
    error: cameraError
  } = useQuery({
    queryFn: async () => {
      return ApiClient.security.getSecurityCameras();
    },
    queryKey: ['security-cameras']
  });

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isValid, isSubmitSuccessful, isSubmitted, isDirty, dirtyFields },
    setError,
    control,
    clearErrors
  } = useForm<SiteFormFields>({
    mode: 'onBlur',
    criteriaMode: 'all',
    reValidateMode: 'onBlur',
    defaultValues: {
      ...(isEdit && siteData
        ? {
            name: siteData.name,
            address: siteData.address,
            city: siteData.city,
            state: siteData.state,
            county: siteData.county,
            zip_code: siteData.zip_code,
            system_size_ac: formatNumericValue(siteData.system_size_ac, true),
            system_size_dc: formatNumericValue(siteData.system_size_dc, true),
            das_connection_name: siteData.das_connection_name,
            telemetry_site_name: siteData.telemetry_site_name,
            lon_lat_url: siteData.lon_lat_url,
            cameras_uuids: siteData.cameras_uuids,
            timezone: siteData.timezone || 'UTC'
          }
        : {
            company_id: companyId,
            name: undefined,
            address: undefined,
            city: undefined,
            state: undefined,
            county: undefined,
            zip_code: undefined,
            system_size_ac: undefined,
            system_size_dc: undefined,
            das_connection_name: undefined,
            telemetry_site_name: undefined,
            lon_lat_url: undefined,
            cameras_uuids: undefined,
            timezone: 'UTC'
          })
    }
  });

  const onSubmit: SubmitHandler<SiteFormFields> = async data => {
    setLoading(true);

    try {
      clearErrors('root');
      const response = await mutateAsync({
        ...(data.company_id && { company_id: data.company_id }),
        name: data.name,
        address: data.address,
        city: data.city,
        state: data.state,
        county: data.county,
        zip_code: data.zip_code,
        system_size_ac: Number.parseFloat(data.system_size_ac.replaceAll(',', '')),
        system_size_dc: Number.parseFloat(data.system_size_dc.replaceAll(',', '')),
        lon_lat_url: data.lon_lat_url,
        cameras_uuids: data.cameras_uuids,
        timezone: data.timezone
      });

      if (dirtyFields.das_connection_name && data.das_connection_name) {
        await saveMappingData({
          id: isEdit ? siteId : response.id,
          attributes: {
            connection_id: selectedConnection?.id,
            telemetry_site_id: selectedSite?.id !== undefined ? String(selectedSite.id) : undefined,
            telemetry_site_name: selectedSite?.name
          }
        });
      }
      queryClient.removeQueries({ queryKey: ['site'] });
      queryClient.removeQueries({ queryKey: ['my-company-site'] });
      queryClient.removeQueries({ queryKey: ['sites'] });
      queryClient.removeQueries({ queryKey: ['camera-alerts'] });
      queryClient.removeQueries({ queryKey: ['cameras'] });
      notify(isEdit ? 'Site has been updated successfully' : 'Site has been successfully created');
      navigate(-1);
    } catch (e: any) {
      setError('root', {
        message: e.response?.data?.message
      });
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    if (cameraError && cameraError instanceof AxiosError) notify(cameraError.message);
  }, [cameraError, notify]);

  return (
    <Stack
      component="form"
      noValidate
      width="30%"
      minWidth="320px"
      spacing={2}
      onSubmit={handleSubmit(onSubmit)}
      sx={{ marginBottom: '20px' }}
    >
      <Typography variant="h6" gutterBottom>
        General Details
      </Typography>
      <TextField
        variant="filled"
        required
        label="Project Name"
        sx={noBottomLineStyles}
        helperText={errors.name?.message}
        error={!!errors.name}
        {...register('name', {
          required: 'Project Name is required field.'
        })}
      />
      <TextField
        variant="filled"
        required
        label="Site Address"
        sx={noBottomLineStyles}
        helperText={errors.address?.message}
        error={!!errors.address}
        {...register('address', {
          required: 'Site Address is required field.'
        })}
      />
      <TextField
        variant="filled"
        required
        label="City"
        sx={noBottomLineStyles}
        helperText={errors.city?.message}
        error={!!errors.city}
        {...register('city', {
          required: 'City is required field.'
        })}
      />
      <Controller
        name="state"
        control={control}
        rules={{ required: 'State is required field.' }}
        render={({ field }) => (
          <SearchableSelect
            options={stateOptions}
            value={field.value ?? null}
            onChange={val => field.onChange(val)}
            onBlur={field.onBlur}
            inputRef={field.ref}
            label="State"
            required
            error={!!errors.state}
            helperText={errors.state?.message}
            variant="filled"
            formControlSx={noBottomLineStyles}
          />
        )}
      />
      <TextField
        variant="filled"
        label="County"
        sx={noBottomLineStyles}
        helperText={errors.county?.message}
        error={!!errors.county}
        {...register('county', {})}
      />
      <TextField
        variant="filled"
        required
        label="Zip Code"
        sx={noBottomLineStyles}
        helperText={errors.zip_code?.message}
        error={!!errors.zip_code}
        inputProps={{
          maxLength: 5
        }}
        {...register('zip_code', {
          required: 'Zip Code is required field.',
          minLength: {
            value: 4,
            message: 'Please use a valid Zip Code not less 4 numbers'
          },
          maxLength: {
            value: 5,
            message: 'Zip Code must not exceed 5 characters'
          },
          pattern: {
            value: /^[0-9]*$/,
            message: 'Zip Code should consist only from numbers'
          }
        })}
      />
      <Controller
        name="system_size_ac"
        control={control}
        rules={{
          required: 'System Size AC is required field.',
          validate: value => {
            const withoutThousandSeparators = (value ?? '').replaceAll(',', '');
            return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
              ? 'Invalid number provided as a value for System Size AC'
              : true;
          }
        }}
        render={({ field }) => (
          <TextField
            variant="filled"
            required
            label="System Size kW AC"
            sx={noBottomLineStyles}
            helperText={errors.system_size_ac?.message}
            error={!!errors.system_size_ac}
            name={field.name}
            disabled={field.disabled}
            value={field.value}
            onChange={field.onChange}
            onBlur={field.onBlur}
            InputProps={{
              inputComponent: FormattedNumericInput as any,
              ref: field.ref
            }}
          />
        )}
      />
      <Controller
        name="system_size_dc"
        control={control}
        rules={{
          required: 'System Size DC is required field.',
          validate: value => {
            const withoutThousandSeparators = (value ?? '').replaceAll(',', '');
            return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
              ? 'Invalid number provided as a value for System Size DC'
              : true;
          }
        }}
        render={({ field }) => (
          <TextField
            variant="filled"
            required
            label="System Size kW DC"
            sx={noBottomLineStyles}
            helperText={errors.system_size_dc?.message}
            error={!!errors.system_size_dc}
            name={field.name}
            disabled={field.disabled}
            value={field.value}
            onChange={field.onChange}
            onBlur={field.onBlur}
            InputProps={{
              inputComponent: FormattedNumericInput as any,
              ref: field.ref
            }}
          />
        )}
      />
      <TextField
        variant="filled"
        required
        label="Latitude/Longitude"
        sx={noBottomLineStyles}
        helperText={
          errors.lon_lat_url?.message ? (
            <span dangerouslySetInnerHTML={{ __html: errors.lon_lat_url.message }} />
          ) : undefined
        }
        error={!!errors.lon_lat_url}
        {...register('lon_lat_url', {
          required: 'Latitude/Longitude is required field.',
          validate: value => {
            const pattern = /^-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?$/;
            if (!pattern.test(value)) {
              return (
                `Provided value doesn't match the expected format. ` +
                'Latitude/Longitude should be provided as a pair of float numbers, separated by a comma, which represent latitude and longitude in decimal degrees. ' +
                '<br />Example: 34.134078, -118.321695 .'
              );
            }
            const [lat, lon] = value.split(',');
            const numeralLat = Number.parseFloat(lat);
            const numberalLon = Number.parseFloat(lon);

            if (numeralLat < -90 || numeralLat > 90)
              return 'Latitude values in decimal degrees range between -90 and +90.';
            if (numberalLon < -180 || numberalLon > 180)
              return 'Longitude values in decimal degrees range between -180 and +180.';
            return true;
          }
        })}
      />
      <Controller
        name="timezone"
        control={control}
        rules={{ required: 'Site Timezone is required field.' }}
        render={({ field }) => (
          <SearchableSelect
            options={timezoneOptions}
            value={field.value ?? null}
            onChange={val => field.onChange(val)}
            onBlur={field.onBlur}
            inputRef={field.ref}
            label="Site Timezone"
            required
            error={!!errors.timezone}
            helperText={
              errors.timezone?.message ||
              "Site's local timezone. Drives site-local performance/reporting (e.g. daily totals); app times still show in your browser's timezone."
            }
            variant="filled"
            formControlSx={noBottomLineStyles}
          />
        )}
      />
      <Typography variant="h6" marginTop="24px" gutterBottom>
        Telemetry
      </Typography>
      <Controller
        name="das_connection_name"
        control={control}
        render={({ field }) => {
          const matchedConnection = connectionData?.items?.find(item => item.name === field.value) || null;
          const isFieldDisabled = (isEdit && !!siteData?.telemetry_site_name) || isLoadingConnectionData;

          const connectionOptions: SearchableSelectOption[] = isFieldDisabled
            ? field.value
              ? [{ label: field.value, value: field.value }]
              : []
            : connectionData?.items?.length
              ? connectionData.items.map(conn => ({ label: conn.name, value: conn.name }))
              : [{ label: 'No connections to show', value: '__none__', disabled: true }];

          return (
            <SearchableSelect
              options={connectionOptions}
              value={matchedConnection ? matchedConnection.name : field.value || null}
              onChange={val => {
                if (val === '__none__') return;
                field.onChange(val);
                setSelectedConnection(connectionData?.items?.find(item => item.name === val) || null);
                setValue('telemetry_site_name', '');
                setSelectedSite(null);
              }}
              onBlur={field.onBlur}
              inputRef={field.ref}
              label="Connection"
              error={!!connectionError || !!errors.das_connection_name}
              helperText={errors.das_connection_name?.message}
              variant="filled"
              disabled={isFieldDisabled}
              loading={isLoadingConnectionData}
              formControlSx={noBottomLineStyles}
            />
          );
        }}
      />
      {(selectedConnection || siteData?.das_connection_name || siteData?.telemetry_site_name) && (
        <Controller
          name="telemetry_site_name"
          control={control}
          rules={{ required: 'Site for Mapping is required field.' }}
          render={({ field }) => {
            const matchedSite = siteMappingData?.items?.find(item => item.name === field.value) || null;
            const isFieldDisabled = (isEdit && !!siteData?.telemetry_site_name) || isLoadingSitesData;

            const siteOptions: SearchableSelectOption[] = isFieldDisabled
              ? field.value
                ? [{ label: field.value, value: field.value }]
                : []
              : siteMappingData?.items?.map(site => ({ label: site.name, value: site.name })) || [];

            return (
              <SearchableSelect
                options={siteOptions}
                value={matchedSite ? matchedSite.name : field.value || null}
                onChange={val => {
                  field.onChange(val);
                  setSelectedSite(siteMappingData?.items?.find(item => item.name === val) || null);
                }}
                onBlur={field.onBlur}
                inputRef={field.ref}
                label="Site for Mapping"
                required
                error={!!siteError || !!errors.telemetry_site_name}
                helperText={errors.telemetry_site_name?.message}
                variant="filled"
                disabled={isFieldDisabled}
                loading={isLoadingSitesData}
                formControlSx={noBottomLineStyles}
              />
            );
          }}
        />
      )}
      <Typography variant="h6" marginTop="24px" gutterBottom>
        Security
      </Typography>
      <Controller
        name="cameras_uuids"
        control={control}
        disabled={isLoadingCameraData}
        render={({ field }) => (
          <SearchableMultiSelect
            options={cameraData?.items.map(cam => ({ label: cam.name, value: cam.uuid })) || []}
            value={field.value || []}
            onChange={field.onChange}
            onBlur={field.onBlur}
            inputRef={field.ref}
            label="Security Cameras"
            error={!!cameraError}
            helperText={cameraError?.message}
            variant="filled"
            disabled={isLoadingCameraData}
            loading={isLoadingCameraData}
            formControlSx={noBottomLineStyles}
          />
        )}
      />
      {errors.root && (
        <Typography px="4px" color="error">
          {errors.root?.message}
        </Typography>
      )}
      {isSubmitted && isSubmitSuccessful && (
        <Typography px="4px" color="green">
          Site was successfully created
        </Typography>
      )}
      <Stack direction="row" width="100%" spacing={3} justifyContent="stretch">
        <Button fullWidth variant="outlined" onClick={() => navigate(-1)}>
          Back
        </Button>
        <Button
          disabled={!isValid || !!errors.root || !isDirty || loading}
          fullWidth
          variant="contained"
          type="submit"
          startIcon={loading ? <CircularProgress color="inherit" size={20} /> : null}
        >
          {isEdit ? 'Update' : 'Add'}
        </Button>
      </Stack>
    </Stack>
  );
};

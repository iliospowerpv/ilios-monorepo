import React, { useState } from 'react';
import { AxiosError } from 'axios';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm, SubmitHandler, Controller } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import Stack from '@mui/material/Stack';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import FormHelperText from '@mui/material/FormHelperText';
import InputLabel from '@mui/material/InputLabel';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import FilledInput from '@mui/material/FilledInput';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Checkbox from '@mui/material/Checkbox';
import ListItemText from '@mui/material/ListItemText';
import HourglassBottomRoundedIcon from '@mui/icons-material/HourglassBottomRounded';

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
};

type SiteFormProps =
  | { mode: 'add'; siteId?: number; siteData?: SiteDetailedInfo; companyId: number }
  | { mode: 'edit'; siteId: number; siteData: SiteDetailedInfo; companyId: number };

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
            cameras_uuids: siteData.cameras_uuids
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
            cameras_uuids: undefined
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
        cameras_uuids: data.cameras_uuids
      });

      if (dirtyFields.das_connection_name && data.das_connection_name) {
        await saveMappingData({
          id: isEdit ? siteId : response.id,
          attributes: {
            connection_id: selectedConnection?.id,
            telemetry_site_id: selectedSite?.id,
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
          <FormControl error={!!errors.state} variant="filled" required sx={noBottomLineStyles}>
            <InputLabel error={!!errors.state}>State</InputLabel>
            <Select
              ref={field.ref}
              value={field.value}
              error={!!errors.state}
              label="state"
              onBlur={field.onBlur}
              onChange={field.onChange}
            >
              {Object.entries(State).map(([key, value]) => (
                <MenuItem key={key} value={key}>
                  {value}
                </MenuItem>
              ))}
            </Select>
            {errors.state?.message && <FormHelperText error>{errors.state.message}</FormHelperText>}
          </FormControl>
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
      <Typography variant="h6" marginTop="24px" gutterBottom>
        Telemetry
      </Typography>
      <Controller
        name="das_connection_name"
        control={control}
        render={({ field }) => {
          const selectedConnection = connectionData?.items?.find(item => item.name === field.value) || null;
          const isFieldDisabled = (isEdit && !!siteData?.telemetry_site_name) || isLoadingConnectionData;

          return (
            <FormControl error={!!errors.das_connection_name} variant="filled" sx={noBottomLineStyles}>
              <InputLabel error={!!errors.das_connection_name}>Connection</InputLabel>
              <Select
                ref={field.ref}
                value={selectedConnection ? selectedConnection.name : field.value || ''}
                error={!!connectionError}
                label="Connection"
                disabled={isFieldDisabled}
                onBlur={field.onBlur}
                IconComponent={isLoadingConnectionData ? HourglassBottomRoundedIcon : undefined}
                onChange={event => {
                  field.onChange(event.target.value);
                  setSelectedConnection(connectionData?.items?.find(item => item.name === event.target.value) || null);
                  setValue('telemetry_site_name', '');
                  setSelectedSite(null);
                }}
              >
                {isFieldDisabled ? (
                  <MenuItem value={field.value}>{field.value}</MenuItem>
                ) : connectionData?.items?.length ? (
                  connectionData?.items?.map(connection => (
                    <MenuItem key={connection.id} value={connection.name}>
                      {connection.name}
                    </MenuItem>
                  ))
                ) : (
                  <MenuItem disabled value="" sx={{ opacity: 0.8 }}>
                    No connections to show
                  </MenuItem>
                )}
              </Select>
              {errors.das_connection_name?.message && (
                <FormHelperText error>{errors.das_connection_name.message}</FormHelperText>
              )}
            </FormControl>
          );
        }}
      />
      {(selectedConnection || siteData?.das_connection_name || siteData?.telemetry_site_name) && (
        <Controller
          name="telemetry_site_name"
          control={control}
          rules={{ required: 'Site for Mapping is required field.' }}
          render={({ field }) => {
            const selectedSite = siteMappingData?.items?.find(item => item.name === field.value) || null;
            const isFieldDisabled = (isEdit && !!siteData?.telemetry_site_name) || isLoadingSitesData;

            return (
              <FormControl error={!!errors.telemetry_site_name} variant="filled" required sx={noBottomLineStyles}>
                <InputLabel error={!!errors.telemetry_site_name}>Site for Mapping</InputLabel>
                <Select
                  ref={field.ref}
                  value={selectedSite ? selectedSite.name : field.value || ''}
                  error={!!siteError}
                  label="Site for Mapping"
                  disabled={isFieldDisabled}
                  onBlur={field.onBlur}
                  IconComponent={isLoadingSitesData ? HourglassBottomRoundedIcon : undefined}
                  onChange={event => {
                    field.onChange(event.target.value);
                    setSelectedSite(siteMappingData?.items?.find(item => item.name === event.target.value) || null);
                  }}
                >
                  {isFieldDisabled ? (
                    <MenuItem value={field.value}>{field.value}</MenuItem>
                  ) : (
                    siteMappingData?.items?.map(site => (
                      <MenuItem key={site.id} value={site.name}>
                        {site.name}
                      </MenuItem>
                    ))
                  )}
                </Select>
                {errors.telemetry_site_name?.message && (
                  <FormHelperText error>{errors.telemetry_site_name.message}</FormHelperText>
                )}
              </FormControl>
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
        render={({ field }) => {
          const selectedValues = field.value || [];

          const handleDelete = (uuidToDelete: string) => {
            const newValues = selectedValues.filter((uuid: string) => uuid !== uuidToDelete);
            field.onChange(newValues);
          };

          return (
            <FormControl variant="filled" error={!!cameraError} sx={noBottomLineStyles}>
              <InputLabel error={!!cameraError} shrink={selectedValues.length > 0}>
                Security Cameras
              </InputLabel>
              <Select
                ref={field.ref}
                value={selectedValues}
                error={!!cameraError}
                label="cameras_uuids"
                multiple
                disabled={isLoadingCameraData}
                onChange={field.onChange}
                onBlur={field.onBlur}
                input={<FilledInput />}
                IconComponent={isLoadingCameraData ? HourglassBottomRoundedIcon : undefined}
                renderValue={selected => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((uuid: string) => {
                      const option = cameraData?.items.find(opt => opt.uuid === uuid);

                      return (
                        <Chip
                          key={uuid}
                          label={option?.name}
                          onDelete={() => handleDelete(uuid)}
                          onMouseDown={event => event.stopPropagation()}
                        />
                      );
                    })}
                  </Box>
                )}
              >
                {cameraData?.items.map(option => (
                  <MenuItem key={option.uuid} value={option.uuid}>
                    <Checkbox checked={selectedValues.indexOf(option.uuid) > -1} />
                    <ListItemText primary={option.name} />
                  </MenuItem>
                ))}
              </Select>
              {cameraError?.message && <FormHelperText error>{cameraError?.message}</FormHelperText>}
            </FormControl>
          );
        }}
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

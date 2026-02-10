import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm, SubmitHandler, Controller } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { isNull } from 'lodash';
import Stack from '@mui/material/Stack';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import FormHelperText from '@mui/material/FormHelperText';
import InputLabel from '@mui/material/InputLabel';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';

import { ApiClient, CompanyAttributes } from '../../../api';
import { COMPANY_TYPES } from '../../../constants';
import { useNotify } from '../../../contexts/notifications/notifications';
import { US_STATES } from '../../../constants/usStates';

const noBottomLineStyles = {
  '& .MuiInputBase-root:not(.Mui-disabled, .Mui-error)': {
    '&::before, &:hover::before, &.Mui-focused::after': {
      borderBottomColor: 'transparent',
      transform: 'scaleX(0)'
    }
  }
};

type CompanyFormProps =
  | { mode: 'add'; companyId?: number; companyData?: CompanyAttributes }
  | { mode: 'edit'; companyId: number; companyData: CompanyAttributes };

interface CreateCompanyFormFields {
  company_type: string;
  name: string;
  address: string;
  city: string;
  state: string;
  county?: string;
  zip_code: string;
  email?: string | null;
  phone?: string | null;
}

interface EditCompanyFormFields {
  company_type?: string;
  name: string;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  county?: string | null;
  zip_code?: string | null;
  email?: string | null;
  phone?: string | null;
}

type CompanyFormFields = CreateCompanyFormFields | EditCompanyFormFields;

export const CompanyForm: React.FC<CompanyFormProps> = props => {
  const { mode, companyData, companyId } = props;
  const [loading, setLoading] = useState(false);
  const { mutateAsync, isPending } = useMutation({
    mutationFn: (attributes: CompanyAttributes) =>
      companyId ? ApiClient.companies.update(companyId, attributes) : ApiClient.companies.create(attributes)
  });
  const isEdit = mode === 'edit';
  const navigate = useNavigate();
  const notify = useNotify();
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    formState: { errors, isValid, isDirty },
    setError,
    control,
    clearErrors,
    trigger
  } = useForm<CompanyFormFields>({
    mode: 'onBlur',
    criteriaMode: 'all',
    reValidateMode: 'onBlur',
    defaultValues: {
      ...(isEdit && companyData
        ? {
            name: companyData.name,
            address: (companyData as any).address,
            city: (companyData as any).city,
            state: (companyData as any).state,
            county: (companyData as any).county,
            zip_code: (companyData as any).zip_code,
            email: (companyData as any).email,
            phone: (companyData as any).phone
          }
        : {
            company_type: undefined,
            name: undefined,
            address: undefined,
            city: undefined,
            state: undefined,
            county: undefined,
            zip_code: undefined,
            email: undefined,
            phone: undefined
          })
    }
  });

  const onSubmit: SubmitHandler<CompanyFormFields> = async data => {
    try {
      clearErrors('root');
      setLoading(true);
      await mutateAsync({
        ...(!isNull(data.company_type) && { company_type: data.company_type }),
        name: data.name,
        address: data.address || null,
        city: (data as any).city || null,
        state: (data as any).state || null,
        county: (data as any).county || null,
        zip_code: (data as any).zip_code || null,
        email: data.email || null,
        phone: data.phone || null
      });
      queryClient.removeQueries({ queryKey: ['company'] });
      notify(isEdit ? 'Company has been updated successfully' : 'Company has been successfully created');
      setTimeout(() => {
        navigate(-1);
        setLoading(false);
      }, 1000);
    } catch (e: any) {
      notify('Something went wrong when adding a new company...');
      setError('root', {
        message: e.response?.data?.message
      });
      setLoading(false);
      setTimeout(() => {
        clearErrors('root');
        trigger();
      }, 5000);
    }
  };

  return (
    <Stack
      component="form"
      data-testid="company__form"
      noValidate
      width="30%"
      minWidth="320px"
      spacing={2}
      onSubmit={handleSubmit(onSubmit)}
    >
      {!isEdit && (
        <Controller
          name="company_type"
          control={control}
          rules={{ required: 'Type is required field.' }}
          render={({ field }) => (
            <FormControl error={!!errors.company_type} variant="filled" required sx={noBottomLineStyles}>
              <InputLabel error={!!errors.company_type}>Type</InputLabel>
              <Select
                ref={field.ref}
                value={field.value}
                error={!!errors.company_type}
                label="Type"
                onBlur={field.onBlur}
                onChange={field.onChange}
              >
                {COMPANY_TYPES &&
                  COMPANY_TYPES.map(type => (
                    <MenuItem key={type} value={type}>
                      {type}
                    </MenuItem>
                  ))}
              </Select>
              {errors.company_type?.message && <FormHelperText error>{errors.company_type?.message}</FormHelperText>}
            </FormControl>
          )}
        />
      )}
      <TextField
        variant="filled"
        required
        label="Name"
        sx={noBottomLineStyles}
        helperText={errors.name?.message}
        error={!!errors.name}
        {...register('name', {
          required: 'Name is required field.',
          minLength: {
            value: 2,
            message: 'Name length should be between 2 and 100 characters.'
          },
          maxLength: {
            value: 100,
            message: 'Name length should be between 2 and 100 characters.'
          }
        })}
      />
      <TextField
        variant="filled"
        required={!isEdit}
        label="Address"
        sx={noBottomLineStyles}
        helperText={(errors as any).address?.message}
        error={!!(errors as any).address}
        {...register('address', {
          ...(!isEdit && { required: 'Address is required field.' }),
          maxLength: {
            value: 255,
            message: 'Address length should be less than 255 characters.'
          }
        })}
      />
      <Box sx={{ display: 'flex', gap: 2 }}>
        <TextField
          variant="filled"
          required={!isEdit}
          label="City"
          sx={{ ...noBottomLineStyles, flex: 1 }}
          helperText={(errors as any).city?.message}
          error={!!(errors as any).city}
          {...register('city' as any, {
            ...(!isEdit && { required: 'City is required field.' }),
            maxLength: {
              value: 100,
              message: 'City length should be less than 100 characters.'
            }
          })}
        />
        <Controller
          name={'state' as any}
          control={control}
          rules={!isEdit ? { required: 'State is required field.' } : {}}
          render={({ field }) => (
            <FormControl
              error={!!(errors as any).state}
              variant="filled"
              required={!isEdit}
              sx={{ ...noBottomLineStyles, minWidth: 120 }}
            >
              <InputLabel error={!!(errors as any).state}>State</InputLabel>
              <Select
                ref={field.ref}
                value={field.value || ''}
                error={!!(errors as any).state}
                label="State"
                onBlur={field.onBlur}
                onChange={field.onChange}
              >
                {US_STATES.map(st => (
                  <MenuItem key={st} value={st}>
                    {st}
                  </MenuItem>
                ))}
              </Select>
              {(errors as any).state?.message && (
                <FormHelperText error>{(errors as any).state?.message}</FormHelperText>
              )}
            </FormControl>
          )}
        />
        <TextField
          variant="filled"
          required={!isEdit}
          label="Zip Code"
          sx={{ ...noBottomLineStyles, width: 120 }}
          helperText={(errors as any).zip_code?.message}
          error={!!(errors as any).zip_code}
          inputProps={{ maxLength: 5 }}
          {...register('zip_code' as any, {
            ...(!isEdit && { required: 'Zip code is required field.' }),
            pattern: {
              value: /^\d{5}$/,
              message: 'Zip code must be exactly 5 digits.'
            }
          })}
        />
      </Box>
      <TextField
        variant="filled"
        label="County (optional)"
        sx={noBottomLineStyles}
        helperText={(errors as any).county?.message}
        error={!!(errors as any).county}
        {...register('county' as any, {
          maxLength: {
            value: 100,
            message: 'County length should be less than 100 characters.'
          }
        })}
      />
      <TextField
        variant="filled"
        label="Email"
        sx={noBottomLineStyles}
        helperText={errors.email?.message}
        error={!!errors.email}
        {...register('email', {
          pattern: {
            value:
              /^(?!.*[.]{2})(?!.*\.@)(?!^[^a-zA-Z0-9]+$)(?![.-])[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+(?<![.])@(?=[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*(?:\.[a-zA-Z]{1,})+$)(?:[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*\.)+[a-zA-Z]{1,}$/,
            message: 'Please provide correct Email.'
          },
          maxLength: {
            value: 100,
            message: 'Email length should be between 3 and 100 characters.'
          }
        })}
      />
      <Controller
        name="phone"
        control={control}
        defaultValue={undefined}
        render={({ field }) => (
          <TextField
            {...field}
            variant="filled"
            label="Phone Number"
            value={field.value || ''}
            sx={noBottomLineStyles}
            helperText={errors.phone?.message}
            error={!!errors.phone}
            onInput={(e: React.ChangeEvent<HTMLInputElement>) => {
              e.target.value = e.target.value.replace(/[^\d]/g, '').slice(0, 10);
            }}
            {...register('phone', {
              pattern: {
                value: /^\d{10}$/,
                message: 'Please provide correct Phone Number.'
              },
              maxLength: {
                value: 10,
                message: 'Phone Number length should be 10 characters.'
              }
            })}
          />
        )}
      />
      <Stack direction="row" width="100%" spacing={3} justifyContent="stretch">
        <Button fullWidth variant="outlined" onClick={() => navigate(-1)}>
          Back
        </Button>
        <Button
          disabled={!isValid || !!errors.root || !isDirty || isPending || loading}
          fullWidth
          variant="contained"
          type="submit"
        >
          {isEdit ? 'Update' : 'Add'}
        </Button>
      </Stack>
      {errors.root && (
        <Typography px="4px" color="error">
          {errors.root?.message}
        </Typography>
      )}
    </Stack>
  );
};

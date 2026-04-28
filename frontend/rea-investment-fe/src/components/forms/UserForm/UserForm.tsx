import * as React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm, SubmitHandler, Controller } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Alert from '@mui/material/Alert';
import Collapse from '@mui/material/Collapse';
import {
  ApiClient,
  CreateUserAttributes,
  UserDetailedInfo,
  EditUserInfoInputPartial,
  ContractorCompany
} from '../../../api';
import { CompaniesSitesMultiselect } from './components/CompaniesSitesMultiselect';
import { useNotify } from '../../../contexts/notifications/notifications';
import { normalizePhone } from '../../../utils/formatters/formatPhoneNumber';
import { SearchableSelect, SearchableSelectOption } from '../../common/SearchableSelect/SearchableSelect';

const noBottomLineStyles = {
  '& .MuiInputBase-root:not(.Mui-disabled, .Mui-error)': {
    '&::before, &:hover::before, &.Mui-focused::after': {
      borderBottomColor: 'transparent',
      transform: 'scaleX(0)'
    }
  }
};

type UserFormFields = {
  email: string;
  phone: string;
  first_name: string;
  last_name: string;
  role_id: number;
  sites_ids: number[];
  parent_company_id: number;
};

type EditUserMutationArgs = {
  userId: number;
  attributes: EditUserInfoInputPartial;
};

type CompanyData = Omit<ContractorCompany, 'email' | 'phone' | 'address'>;

type UserFormProps =
  | { mode: 'add'; userId?: number; userData?: UserDetailedInfo; level?: 'system'; companyData?: CompanyData }
  | { mode: 'edit'; userId: number; userData: UserDetailedInfo; level?: 'system'; companyData?: CompanyData }
  | { mode: 'add'; userId?: number; userData?: UserDetailedInfo; level: 'company'; companyData: CompanyData }
  | { mode: 'edit'; userId: number; userData: UserDetailedInfo; level: 'company'; companyData: CompanyData };

export const UserForm: React.FC<UserFormProps> = ({ mode, userData, userId, level, companyData }) => {
  const notify = useNotify();
  const queryClient = useQueryClient();

  const { mutateAsync: createUser } = useMutation({
    mutationFn: (attributes: CreateUserAttributes) => ApiClient.user.create(attributes)
  });

  const { mutateAsync: editUser } = useMutation({
    mutationFn: (args: EditUserMutationArgs) => ApiClient.user.edit(args.userId, args.attributes)
  });

  const navigate = useNavigate();

  const { handleSubmit, formState, setError, setValue, control, reset, clearErrors, watch, trigger } =
    useForm<UserFormFields>({
      mode: 'onBlur',
      criteriaMode: 'all',
      reValidateMode: 'onBlur',
      defaultValues: {
        first_name: undefined,
        last_name: undefined,
        email: undefined,
        phone: undefined,
        role_id: undefined,
        parent_company_id: undefined,
        sites_ids: undefined
      }
    });

  const onSubmit: SubmitHandler<UserFormFields> = async data => {
    if (mode === 'edit') {
      try {
        await editUser({
          userId,
          attributes: {
            email: data.email,
            phone: normalizePhone(data.phone),
            role_id: data.role_id,
            parent_company_id: data.parent_company_id,
            sites_ids: data.sites_ids
          }
        });
        queryClient.removeQueries({ queryKey: ['users'] });
        notify(`User ${userData.first_name} ${userData.last_name} was updated`);
        setTimeout(() => navigate(level === 'company' ? '/settings/my-company/users' : '/settings/users'), 1000);
      } catch (e: any) {
        notify('Something went wrong when editing a user...');
        setError('root', {
          message: e.response?.data?.message || 'User update failed'
        });
        setTimeout(() => {
          clearErrors('root');
          trigger();
        }, 5000);
      }
      return;
    }

    try {
      const normalizedData = { ...data, phone: normalizePhone(data.phone) };
      const message = await createUser(normalizedData);
      notify(message?.message);
      reset();
      queryClient.removeQueries({ queryKey: ['my-company-users'] });
      setTimeout(() => navigate(level === 'company' ? '/settings/my-company/users' : '/settings/users'), 1000);
    } catch (e: any) {
      notify('Something went wrong when adding a new user...');
      setError('root', {
        message: e.response?.data?.message || 'User creation failed'
      });
      setTimeout(() => {
        clearErrors('root');
        trigger();
      }, 5000);
    }
  };

  const {
    data: companiesSites,
    error: companiesSitesRetrievingError,
    isLoading: isLoadingCompaniesSites
  } = useQuery({
    queryFn: ApiClient.companies.sites,
    queryKey: ['companies-sites-select']
  });

  const {
    data: rolesWithCompanyType,
    error: rolesRetrievingError,
    isLoading: isLoadingRoles
  } = useQuery({
    queryFn: ApiClient.companies.rolesWithCompanyType,
    queryKey: ['roles-with-company-type-select']
  });

  const {
    data: contractors,
    error: contractorsRetrievingError,
    isLoading: isLoadingContractors
  } = useQuery({
    queryFn: () => ApiClient.companies.contractors({ limit: 10000 }),
    queryKey: ['contractors-select'],
    initialData: level === 'company' ? { skip: 0, limit: 1, total: 1, items: [companyData] } : undefined,
    enabled: level !== 'company'
  });

  const [formReady, setFormReady] = React.useState(false);

  React.useEffect(() => {
    const isLoadingOptions = isLoadingCompaniesSites || isLoadingRoles || isLoadingContractors;
    const hasLoadingOptionsErrors =
      !!contractorsRetrievingError || !!rolesRetrievingError || !!contractorsRetrievingError;
    const formReady =
      !isLoadingOptions && !hasLoadingOptionsErrors && contractors && companiesSites && rolesWithCompanyType;

    if (formReady) {
      setFormReady(true);
    }
  }, [
    isLoadingCompaniesSites,
    isLoadingRoles,
    isLoadingContractors,
    contractorsRetrievingError,
    rolesRetrievingError,
    contractors,
    companiesSites,
    rolesWithCompanyType
  ]);

  const [isFilledWithInitialData, setIsFilledWithInitialData] = React.useState(false);

  React.useEffect(() => {
    if (mode === 'edit' && !isFilledWithInitialData && formReady) {
      reset({
        first_name: userData.first_name,
        last_name: userData.last_name,
        email: userData.email,
        phone: userData.phone,
        parent_company_id: userData.parent_company.id,
        role_id: userData.role.id,
        sites_ids: userData.sites.map(site => site.id)
      });
      setIsFilledWithInitialData(true);
    } else if (mode === 'add' && level === 'company' && !isFilledWithInitialData && formReady) {
      reset({
        first_name: undefined,
        last_name: undefined,
        email: undefined,
        phone: undefined,
        parent_company_id: companyData.id,
        role_id: undefined,
        sites_ids: undefined
      });
      setIsFilledWithInitialData(true);
    }
  }, [mode, isFilledWithInitialData, formReady, reset, userData, level, companyData]);

  const { errors, isValid, isSubmitted, isSubmitSuccessful, isSubmitting, isDirty } = formState;
  const companyId = watch('parent_company_id');

  React.useEffect(() => {
    const subscription = watch((_value, { name, type }) => {
      if (
        name === 'parent_company_id' &&
        ['change', 'changeText', 'valueChange', 'selectionChange'].includes(type || '')
      ) {
        setValue('role_id', '' as unknown as number);
      }
    });

    return () => subscription.unsubscribe();
  }, [watch, setValue]);

  const handleClickBack = () => navigate(-1);

  const selectedCompany = contractors?.items.find(company => company.id === companyId);
  const disableRoleSelection = !selectedCompany || isLoadingRoles || !!rolesRetrievingError;
  const roleOptions =
    selectedCompany && rolesWithCompanyType
      ? rolesWithCompanyType.data.filter(role => role.company_type === selectedCompany.company_type)
      : [...((!!rolesWithCompanyType && rolesWithCompanyType.data) || [])];

  const companyOptions: SearchableSelectOption[] =
    contractors?.items.map(company => ({
      label: company.name,
      value: company.id
    })) || [];

  const roleSelectOptions: SearchableSelectOption[] = roleOptions.map(({ role }) => ({
    label: role.name,
    value: role.id
  }));

  return (
    <Stack component="form" noValidate width="30%" minWidth="320px" spacing={2} onSubmit={handleSubmit(onSubmit)}>
      <Controller
        name="first_name"
        control={control}
        rules={{
          required: 'First Name is required field.',
          pattern: {
            value: /^[\p{L}\s'\u2019.-]+$/u,
            message: 'First Name should contain only letters, spaces, hyphens, apostrophes, or periods.'
          },
          minLength: {
            value: 2,
            message: 'First Name length should be between 2 and 100 characters.'
          },
          maxLength: {
            value: 100,
            message: 'First Name length should be between 2 and 100 characters.'
          }
        }}
        render={({ field: { ref, value, ...field } }) => (
          <TextField
            {...field}
            variant="filled"
            required
            disabled={mode === 'edit' || !formReady}
            label="First Name"
            sx={noBottomLineStyles}
            helperText={errors.first_name?.message}
            error={!!errors.first_name}
            inputRef={ref}
            value={value || ''}
          />
        )}
      />
      <Controller
        name="last_name"
        control={control}
        rules={{
          required: 'Last Name is required field.',
          pattern: {
            value: /^[\p{L}\s'\u2019.-]+$/u,
            message: 'Last Name should contain only letters, spaces, hyphens, apostrophes, or periods.'
          },
          minLength: {
            value: 2,
            message: 'Last Name length should be between 2 and 100 characters.'
          },
          maxLength: {
            value: 100,
            message: 'Last Name length should be between 2 and 100 characters.'
          }
        }}
        render={({ field: { ref, value, ...field } }) => (
          <TextField
            {...field}
            variant="filled"
            required
            disabled={mode === 'edit' || !formReady}
            label="Last Name"
            sx={noBottomLineStyles}
            helperText={errors.last_name?.message}
            error={!!errors.last_name}
            inputRef={ref}
            value={value || ''}
          />
        )}
      />
      <Controller
        name="email"
        control={control}
        disabled={!formReady}
        rules={{
          required: 'Email is required field.',
          pattern: {
            value:
              /^(?!.*[.]{2})(?!.*\.@)(?!^[^a-zA-Z0-9]+$)(?![.-])[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+(?<![.])@(?=[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*(?:\.[a-zA-Z]{1,})+$)(?:[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*\.)+[a-zA-Z]{1,}$/,
            message: 'Please provide correct Email.'
          },
          maxLength: {
            value: 100,
            message: 'Email length should be between 3 and 100 characters.'
          }
        }}
        render={({ field: { ref, value, ...field } }) => (
          <TextField
            variant="filled"
            required
            label="Email"
            sx={noBottomLineStyles}
            helperText={errors.email?.message}
            error={!!errors.email}
            inputRef={ref}
            value={value || ''}
            {...field}
          />
        )}
      />
      <Controller
        name="phone"
        control={control}
        disabled={!formReady}
        rules={{
          required: 'Phone Number is required field.',
          validate: value => {
            if (!value) return 'Phone Number is required field.';
            return normalizePhone(value).length === 10 || 'Phone number must contain exactly 10 digits.';
          }
        }}
        render={({ field: { ref, value, ...field } }) => (
          <TextField
            variant="filled"
            label="Phone Number"
            required
            sx={noBottomLineStyles}
            helperText={errors.phone?.message || 'e.g. (555) 123-4567'}
            error={!!errors.phone}
            inputRef={ref}
            value={value || ''}
            {...field}
          />
        )}
      />
      <Controller
        name="parent_company_id"
        control={control}
        rules={{ required: 'Company is required field.' }}
        render={({ field }) => (
          <SearchableSelect
            options={companyOptions}
            value={field.value || null}
            onChange={val => field.onChange(val)}
            onBlur={field.onBlur}
            inputRef={field.ref}
            label="Company"
            required
            error={!!contractorsRetrievingError || !!errors.parent_company_id}
            helperText={errors.parent_company_id?.message || contractorsRetrievingError?.message}
            variant="filled"
            disabled={!formReady || level === 'company'}
            loading={isLoadingContractors}
            formControlSx={noBottomLineStyles}
          />
        )}
      />
      <Controller
        name="role_id"
        control={control}
        rules={{ required: 'Role is required field.' }}
        disabled={!formReady || disableRoleSelection}
        render={({ field }) => (
          <SearchableSelect
            options={roleSelectOptions}
            value={field.value || null}
            onChange={val => field.onChange(val)}
            onBlur={field.onBlur}
            inputRef={field.ref}
            label="Role"
            required
            error={!!rolesRetrievingError || !!errors.role_id}
            helperText={errors.role_id?.message || rolesRetrievingError?.message}
            variant="filled"
            disabled={field.disabled}
            loading={isLoadingRoles}
            formControlSx={noBottomLineStyles}
          />
        )}
      />
      <Controller
        name="sites_ids"
        control={control}
        disabled={!formReady}
        rules={{ required: 'Project Access is required field.' }}
        render={({ field }) => (
          <CompaniesSitesMultiselect
            data={companiesSites?.data || []}
            optionsLoading={isLoadingCompaniesSites}
            loadingError={companiesSitesRetrievingError}
            validationError={errors.sites_ids}
            disabled={field.disabled}
            onBlur={field.onBlur}
            value={field.value || []}
            onChange={field.onChange}
          />
        )}
      />
      <Stack direction="row" width="100%" spacing={3} justifyContent="stretch">
        <Button fullWidth variant="outlined" onClick={handleClickBack}>
          Back
        </Button>
        <Button disabled={!isValid || !isDirty || isSubmitting} fullWidth variant="contained" type="submit">
          {mode === 'add' ? 'Add' : 'Update'}
        </Button>
      </Stack>
      <Collapse in={isSubmitted && !isSubmitSuccessful && !!errors.root}>
        <Alert severity="error">{errors.root?.message}</Alert>
      </Collapse>
    </Stack>
  );
};

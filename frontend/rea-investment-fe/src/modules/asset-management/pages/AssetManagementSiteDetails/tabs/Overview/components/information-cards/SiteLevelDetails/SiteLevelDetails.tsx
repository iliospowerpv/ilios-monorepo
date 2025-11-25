import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import Table from '@mui/material/Table';
import TableRow from '@mui/material/TableRow';
import TableBody from '@mui/material/TableBody';
import dayjs from 'dayjs';
import CustomParseFormatPlugin from 'dayjs/plugin/customParseFormat';
dayjs.extend(CustomParseFormatPlugin);

import { FieldCell, TextBox } from '../../InformationCardBase/InformationCardBase.styles';
import {
  InformationCardFormProps,
  InformationCardFormRef,
  InformationCardBase
} from '../../InformationCardBase/InformationCardBase';
import { useNotify } from '../../../../../../../../../contexts/notifications/notifications';

import { ApiClient } from '../../../../../../../../../api';
import FormHelperText from '@mui/material/FormHelperText';
import formFloatValue from '../../../../../../../../../utils/formatters/formatFloatValue';
import formatPercentageValue from '../../../../../../../../../utils/formatters/formatPercentageValue';
import IconButton from '@mui/material/IconButton';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import Visibility from '@mui/icons-material/Visibility';
import Link from '@mui/material/Link';
import { StyledSelectItem } from '../../../../../../DeviceDetails/tabs/Overview/components/GeneralDeviceInfoCard/GeneralDeviceInfoCard.styles';

type SiteLevelDetailsData = Exclude<
  Awaited<ReturnType<typeof ApiClient.assetManagement.siteInfo>>['site_level_details'],
  null
>;

interface SiteLevelDetailsFormFields {
  status: string | null;
  project_id: string | null;
  pvsyst: string | null;
  greenhouse_gas_offset: string | null;
  incentive_program: string | null;
  das_provider: string | null;
  das_account: string | null;
  das_username: string | null;
  das_password: string | null;
}

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

export const PasswordTextField: React.FC<{ password: string | null | undefined }> = ({ password }) => {
  const [isRevealed, setIsRevealed] = React.useState(false);

  const togglePasswordRevealed = React.useCallback(() => {
    setIsRevealed(isRevealed => !isRevealed);
  }, [setIsRevealed]);

  if (!password?.length) return null;

  return (
    <Box display="flex" flexDirection="row" justifyContent="end">
      <div>{isRevealed ? password : '❋'.repeat(8)}</div>
      <IconButton size="small" sx={{ ml: '4px', width: '20px', height: '20px' }} onClick={togglePasswordRevealed}>
        {isRevealed ? <VisibilityOff /> : <Visibility />}
      </IconButton>
    </Box>
  );
};

const HyperlinkField: React.FC<{ link: string | null | undefined }> = ({ link }) => {
  return link ? (
    <Box sx={{ whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
      <Link href={link} rel="noreferrer" target="_blank">
        {link}
      </Link>
    </Box>
  ) : null;
};

const SiteLevelDetailsForm = React.forwardRef<InformationCardFormRef, InformationCardFormProps<SiteLevelDetailsData>>(
  ({ mode, setMode, siteId, data, reflectFormState }, ref) => {
    const queryClient = useQueryClient();
    const notify = useNotify();

    const { handleSubmit, formState, control, reset } = useForm<SiteLevelDetailsFormFields>({
      mode: 'onChange',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        status: data.status,
        project_id: data.project_id,
        pvsyst: data.pvsyst,
        greenhouse_gas_offset: data.greenhouse_gas_offset,
        incentive_program: data.incentive_program,
        das_provider: data.das_provider,
        das_account: data.das_account,
        das_username: data.das_username,
        das_password: data.das_password
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateSiteLevelDetailsDetails } = useMutation({
      mutationFn: (attributes: SiteLevelDetailsFormFields) =>
        ApiClient.assetManagement.updateSiteInfo({
          siteId,
          section: 'site_level_details',
          data: {
            status: attributes.status,
            project_id: attributes.project_id,
            pvsyst: attributes.pvsyst,
            greenhouse_gas_offset: attributes.greenhouse_gas_offset,
            incentive_program: attributes.incentive_program,
            das_provider: attributes.das_provider,
            das_account: attributes.das_account,
            das_username: attributes.das_username,
            das_password: attributes.das_password
          }
        })
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
        status: data.status,
        project_id: data.project_id,
        pvsyst: data.pvsyst,
        greenhouse_gas_offset: data.greenhouse_gas_offset,
        incentive_program: data.incentive_program,
        das_provider: data.das_provider,
        das_account: data.das_account,
        das_username: data.das_username,
        das_password: data.das_password
      });
    }, [data, reset]);

    const onSubmit: SubmitHandler<SiteLevelDetailsFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateSiteLevelDetailsDetails(data);
          notify(response.message || `Site Level Details information was successfully updated.`);
          reset({
            status: data.status,
            project_id: data.project_id,
            pvsyst: data.pvsyst,
            greenhouse_gas_offset: data.greenhouse_gas_offset,
            incentive_program: data.incentive_program,
            das_provider: data.das_provider,
            das_account: data.das_account,
            das_username: data.das_username,
            das_password: data.das_password
          });
          await queryClient.invalidateQueries({ queryKey: ['sites'] });
          setMode('view');
        } catch (e: any) {
          notify(
            e.response?.data?.message || 'Something went wrong when updating the Site Level Details information...'
          );
        }
      },
      [notify, queryClient, reset, setMode, updateSiteLevelDetailsDetails]
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
        <Table sx={{ width: '100%', height: 'auto', tableLayout: 'fixed' }} size="small">
          <TableBody>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Site Name:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.name}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Project ID:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.project_id}</TextBox>
                ) : (
                  <Controller
                    name="project_id"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Project ID length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.project_id}
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
            {errors.project_id?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.project_id?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Status:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.status}</TextBox>
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
                        disabled={isSubmitting}
                        InputProps={{
                          sx: inputStyles
                        }}
                        select
                        fullWidth
                        variant="outlined"
                        size="small"
                      >
                        {['Construction', 'Decommissioned', 'Placed in Service', 'Sold'].map(status => (
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
            {errors.status?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.status?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Address:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.address}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>City:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.city}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>State:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.state}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Zip Code:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.zip_code}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>County:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.county}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Latitude/Longitude:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.lon_lat_url}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>System Size kW DC:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{formFloatValue(data.system_size_dc)}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>System Size kW AC:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{formFloatValue(data.system_size_ac)}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>PVSYST:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <HyperlinkField link={data.pvsyst} />
                ) : (
                  <Controller
                    name="pvsyst"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        if (value.length < 2) return 'PVSYST length should be more than 2 symbols.';
                        return (
                          /^(https?:\/\/)?([\w\d-]+\.)+[a-z]{2,}(\/.*)?$/.test(value) || 'Please enter a valid link.'
                        );
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.pvsyst}
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
            {errors.pvsyst?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.pvsyst?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Greenhouse Gas Offset:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.greenhouse_gas_offset}</TextBox>
                ) : (
                  <Controller
                    name="greenhouse_gas_offset"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Greenhouse Gas Offset length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.greenhouse_gas_offset}
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
            {errors.greenhouse_gas_offset?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.greenhouse_gas_offset?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Incentive Program:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.incentive_program}</TextBox>
                ) : (
                  <Controller
                    name="incentive_program"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Incentive Program length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.incentive_program}
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
            {errors.incentive_program?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.incentive_program?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Data Acquisition System Provider (DAS):</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.das_provider}</TextBox>
                ) : (
                  <Controller
                    name="das_provider"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Data Acquisition System Provider (DAS) length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.das_provider}
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
            {errors.das_provider?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.das_provider?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Account #:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.das_account}</TextBox>
                ) : (
                  <Controller
                    name="das_account"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Account length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.das_account}
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
            {errors.das_account?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.das_account?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Username:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.das_username}</TextBox>
                ) : (
                  <Controller
                    name="das_username"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Username length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.das_username}
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
            {errors.das_username?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.das_username?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Password:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <PasswordTextField password={data.das_password} />
                ) : (
                  <Controller
                    name="das_password"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Password length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.das_password}
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
            {errors.das_password?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.das_password?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}

            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Year 1 Expected Production:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.year_one_expected_production}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Degradation Amount, %:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.degradation_amount}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Capacity as % of Total Portfolio:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{formatPercentageValue(data.capacity_as_percent_of_total_portfolio)}</TextBox>
              </FieldCell>
            </TableRow>
          </TableBody>
        </Table>
      </Box>
    );
  }
);

SiteLevelDetailsForm.displayName = 'SiteLevelDetailsForm';

interface SiteLevelDetailsCardProps {
  siteId: number;
  data: SiteLevelDetailsData;
}

export const SiteLevelDetailsCard: React.FC<SiteLevelDetailsCardProps> = ({ siteId, data }) => (
  <InformationCardBase<SiteLevelDetailsData>
    title="Site Level Details"
    informationCardData={data}
    siteId={siteId}
    InformationCardForm={SiteLevelDetailsForm}
  />
);

import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import dayjs, { Dayjs } from 'dayjs';
import CustomParseFormatPlugin from 'dayjs/plugin/customParseFormat';
import { DatePicker } from '@mui/x-date-pickers';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import Table from '@mui/material/Table';
import TableRow from '@mui/material/TableRow';
import TableBody from '@mui/material/TableBody';
import FormHelperText from '@mui/material/FormHelperText';

import { FieldCell, TextBox } from '../../InformationCardBase/InformationCardBase.styles';
import {
  InformationCardFormProps,
  InformationCardFormRef,
  InformationCardBase
} from '../../InformationCardBase/InformationCardBase';
import { useNotify } from '../../../../../../../../../contexts/notifications/notifications';

import { ApiClient } from '../../../../../../../../../api';
import { StyledSelectItem } from '../../../../../../DeviceDetails/tabs/Overview/components/GeneralDeviceInfoCard/GeneralDeviceInfoCard.styles';

dayjs.extend(CustomParseFormatPlugin);

type OfftakerCardData = Exclude<Awaited<ReturnType<typeof ApiClient.assetManagement.siteInfo>>['offtaker'], null>;

interface OfftakerFormFields {
  name: string | null;
  offtaker_type: string | null;
  credit_rating: string | null;
  rating_agency: string | null;
  date_of_rating: Dayjs | null;
}

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

const OfftakerForm = React.forwardRef<InformationCardFormRef, InformationCardFormProps<OfftakerCardData>>(
  ({ mode, setMode, siteId, data, reflectFormState }, ref) => {
    const queryClient = useQueryClient();
    const notify = useNotify();

    const { handleSubmit, formState, control, reset } = useForm<OfftakerFormFields>({
      mode: 'onChange',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        name: data.offtaker_name || null,
        offtaker_type: data.offtaker_type || null,
        credit_rating: data.credit_rating || null,
        rating_agency: data.rating_agency || null,
        date_of_rating: data.date_of_rating ? dayjs(data.date_of_rating, 'YYYY-MM-DD', true) : null
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateOfftakerDetails } = useMutation({
      mutationFn: (attributes: OfftakerFormFields) =>
        ApiClient.assetManagement.updateSiteInfo({
          siteId,
          section: 'offtaker',
          data: {
            offtaker_name: attributes.name || null,
            offtaker_type: attributes.offtaker_type || null,
            credit_rating: attributes.credit_rating || null,
            rating_agency: attributes.rating_agency || null,
            date_of_rating: attributes.date_of_rating ? attributes.date_of_rating.format('YYYY-MM-DD') : null
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
        name: data.offtaker_name || null,
        offtaker_type: data.offtaker_type || null,
        credit_rating: data.credit_rating || null,
        rating_agency: data.rating_agency || null,
        date_of_rating: data.date_of_rating ? dayjs(data.date_of_rating, 'YYYY-MM-DD', true) : null
      });
    }, [data, reset]);

    const onSubmit: SubmitHandler<OfftakerFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateOfftakerDetails(data);
          notify(response.message || `Offtaker information was successfully updated.`);
          reset(data);
          queryClient.invalidateQueries({ queryKey: ['sites'] });
          setMode('view');
        } catch (e: any) {
          notify(e.response?.data?.message || 'Something went wrong when updating the Offtaker information...');
        }
      },
      [notify, queryClient, reset, setMode, updateOfftakerDetails]
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
                <TextBox fieldName>Offtaker Name:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.offtaker_name}</TextBox>
                ) : (
                  <Controller
                    name="name"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Offtaker Name length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.name}
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
            {errors.name?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.name?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Offtaker Type:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.offtaker_type}</TextBox>
                ) : (
                  <Controller
                    name="offtaker_type"
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
                        {['Community Solar', 'Individual', 'Utility Provider'].map(status => (
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
            {errors.offtaker_type?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.offtaker_type?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Offtaker Credit Rating:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.credit_rating}</TextBox>
                ) : (
                  <Controller
                    name="credit_rating"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Offtaker Credit Rating length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        required
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.credit_rating}
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
            {errors.credit_rating?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.credit_rating?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Ratings Agency:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.rating_agency}</TextBox>
                ) : (
                  <Controller
                    name="rating_agency"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Ratings Agency length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.rating_agency}
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
            {errors.rating_agency?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.rating_agency?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Date of Rating:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {data.date_of_rating ? dayjs(data.date_of_rating, 'YYYY-MM-DD', true).format('MM/DD/YYYY') : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="date_of_rating"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        return dayjs(value).isValid() || 'Please enter correct Date of Rating.';
                      }
                    }}
                    render={({ field: { ref, value, onChange, onBlur, ...field } }) => (
                      <DatePicker
                        {...field}
                        value={value}
                        format="MM/DD/YYYY"
                        inputRef={ref}
                        onChange={val => onChange(val)}
                        slotProps={{
                          textField: {
                            onBlur,
                            disabled: isSubmitting,
                            error: !!errors.date_of_rating,
                            size: 'small',
                            fullWidth: true,
                            InputProps: { sx: inputStyles },
                            variant: 'outlined'
                          }
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            {errors.date_of_rating?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.date_of_rating?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Box>
    );
  }
);

OfftakerForm.displayName = 'OfftakerForm';

interface OfftakerCardProps {
  siteId: number;
  data: OfftakerCardData;
}

export const OfftakerCard: React.FC<OfftakerCardProps> = ({ siteId, data }) => (
  <InformationCardBase<OfftakerCardData>
    title="Offtaker"
    informationCardData={data}
    siteId={siteId}
    InformationCardForm={OfftakerForm}
  />
);

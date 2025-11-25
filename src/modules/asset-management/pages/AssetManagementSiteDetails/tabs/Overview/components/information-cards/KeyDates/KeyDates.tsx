import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import dayjs, { Dayjs } from 'dayjs';
import CustomParseFormatPlugin from 'dayjs/plugin/customParseFormat';
import { DatePicker } from '@mui/x-date-pickers';
import Box from '@mui/material/Box';
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

dayjs.extend(CustomParseFormatPlugin);

type KeyDatesCardData = Exclude<Awaited<ReturnType<typeof ApiClient.assetManagement.siteInfo>>['key_dates'], null>;

interface KeyDatesFormFields {
  permission_to_operate: Dayjs | null;
  placed_in_service_date: Dayjs | null;
  financial_close_date: Dayjs | null;
}

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

const KeyDatesForm = React.forwardRef<InformationCardFormRef, InformationCardFormProps<KeyDatesCardData>>(
  ({ mode, setMode, siteId, data, reflectFormState }, ref) => {
    const queryClient = useQueryClient();
    const notify = useNotify();

    const { handleSubmit, formState, control, reset } = useForm<KeyDatesFormFields>({
      mode: 'all',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        permission_to_operate: data.permission_to_operate
          ? dayjs(data.permission_to_operate, 'YYYY-MM-DD', true)
          : null,
        placed_in_service_date: data.placed_in_service_date
          ? dayjs(data.placed_in_service_date, 'YYYY-MM-DD', true)
          : null,
        financial_close_date: data.financial_close_date ? dayjs(data.financial_close_date, 'YYYY-MM-DD', true) : null
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateKeyDatesDetails } = useMutation({
      mutationFn: (attributes: KeyDatesFormFields) =>
        ApiClient.assetManagement.updateSiteInfo({
          siteId,
          section: 'key_dates',
          data: {
            permission_to_operate: attributes.permission_to_operate
              ? attributes.permission_to_operate.format('YYYY-MM-DD')
              : null,
            placed_in_service_date: attributes.placed_in_service_date
              ? attributes.placed_in_service_date.format('YYYY-MM-DD')
              : null,
            financial_close_date: attributes.financial_close_date
              ? attributes.financial_close_date.format('YYYY-MM-DD')
              : null
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
        permission_to_operate: data.permission_to_operate
          ? dayjs(data.permission_to_operate, 'YYYY-MM-DD', true)
          : null,
        placed_in_service_date: data.placed_in_service_date
          ? dayjs(data.placed_in_service_date, 'YYYY-MM-DD', true)
          : null,
        financial_close_date: data.financial_close_date ? dayjs(data.financial_close_date, 'YYYY-MM-DD', true) : null
      });
    }, [data, reset]);

    const onSubmit: SubmitHandler<KeyDatesFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateKeyDatesDetails(data);
          notify(response.message || `Key dates information was successfully updated.`);
          reset(data);
          queryClient.invalidateQueries({ queryKey: ['sites'] });
          setMode('view');
        } catch (e: any) {
          notify(e.response?.data?.message || 'Something went wrong when updating the Key Dates information...');
        }
      },
      [notify, queryClient, reset, setMode, updateKeyDatesDetails]
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
                <TextBox fieldName>Mechanical Completion Date:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.mechanical_completion_date}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Substantial Completion Date:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.substantial_completion_date}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Final Completion Date:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.final_completion_date}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Permission to Operate:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {data.permission_to_operate
                      ? dayjs(data.permission_to_operate, 'YYYY-MM-DD', true).format('MM/DD/YYYY')
                      : null}
                  </TextBox>
                ) : (
                  <Controller
                    name="permission_to_operate"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        return dayjs(value).isValid() || 'Please enter correct Permission to Operate.';
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
                            error: !!errors.permission_to_operate,
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
            {errors.permission_to_operate?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.permission_to_operate?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Placed in Service Date:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {data.placed_in_service_date
                      ? dayjs(data.placed_in_service_date, 'YYYY-MM-DD', true).format('MM/DD/YYYY')
                      : null}
                  </TextBox>
                ) : (
                  <Controller
                    name="placed_in_service_date"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        return dayjs(value).isValid() || 'Please enter correct Placed in Service Date.';
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
                            error: !!errors.placed_in_service_date,
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
            {errors.placed_in_service_date?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.placed_in_service_date?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Financial Close Date:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {data.financial_close_date
                      ? dayjs(data.financial_close_date, 'YYYY-MM-DD', true).format('MM/DD/YYYY')
                      : null}
                  </TextBox>
                ) : (
                  <Controller
                    name="financial_close_date"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        return dayjs(value).isValid() || 'Please enter correct Financial Close Date.';
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
                            error: !!errors.financial_close_date,
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
            {errors.financial_close_date?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.financial_close_date?.message}
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

KeyDatesForm.displayName = 'KeyDatesForm';

interface KeyDatesCardProps {
  siteId: number;
  data: KeyDatesCardData;
}

export const KeyDatesCard: React.FC<KeyDatesCardProps> = ({ siteId, data }) => (
  <InformationCardBase<KeyDatesCardData>
    title="Key Dates"
    informationCardData={data}
    siteId={siteId}
    InformationCardForm={KeyDatesForm}
  />
);

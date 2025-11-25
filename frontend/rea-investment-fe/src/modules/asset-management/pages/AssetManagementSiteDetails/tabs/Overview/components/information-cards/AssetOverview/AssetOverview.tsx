import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import Table from '@mui/material/Table';
import TableRow from '@mui/material/TableRow';
import TableBody from '@mui/material/TableBody';

import { FieldCell, TextBox } from '../../InformationCardBase/InformationCardBase.styles';
import {
  InformationCardFormProps,
  InformationCardFormRef,
  InformationCardBase
} from '../../InformationCardBase/InformationCardBase';
import { useNotify } from '../../../../../../../../../contexts/notifications/notifications';

import { ApiClient } from '../../../../../../../../../api';
import { StyledSelectItem } from '../../../../../../DeviceDetails/tabs/Overview/components/TechnicalDetailCard/TechnicalDetail.styles';
import FormHelperText from '@mui/material/FormHelperText';
import formatFloatValue from '../../../../../../../../../utils/formatters/formatFloatValue';
import FormattedNumericInputWithMinus from '../../../../../../../../../components/common/FormattedNumericInput/FormattedNumericInputWithMinus';

type AssetOverviewCardData = Exclude<
  Awaited<ReturnType<typeof ApiClient.assetManagement.siteInfo>>['asset_overview'],
  null
>;
type AssetOverviewFormFields = Pick<
  AssetOverviewCardData,
  'battery_storage' | 'mount_type' | 'dc_wiring_loss' | 'ac_wiring_loss' | 'medium_voltage_loss' | 'mv_line_loss'
>;

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

const AssetOverviewForm = React.forwardRef<InformationCardFormRef, InformationCardFormProps<AssetOverviewCardData>>(
  ({ mode, setMode, siteId, data, reflectFormState }, ref) => {
    const queryClient = useQueryClient();
    const notify = useNotify();

    const { handleSubmit, formState, control, reset } = useForm<AssetOverviewFormFields>({
      mode: 'onChange',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        battery_storage: data.battery_storage,
        mount_type: data.mount_type,
        dc_wiring_loss: data.dc_wiring_loss,
        ac_wiring_loss: data.ac_wiring_loss,
        medium_voltage_loss: data.medium_voltage_loss,
        mv_line_loss: data.mv_line_loss
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateAssetOverviewDetails } = useMutation({
      mutationFn: (attributes: AssetOverviewFormFields) =>
        ApiClient.assetManagement.updateSiteInfo({
          siteId,
          section: 'asset_overview',
          data: {
            battery_storage: attributes.battery_storage || null,
            mount_type: attributes.mount_type || null,
            dc_wiring_loss: attributes.dc_wiring_loss || null,
            ac_wiring_loss: attributes.ac_wiring_loss || null,
            medium_voltage_loss: attributes.medium_voltage_loss || null,
            mv_line_loss: attributes.mv_line_loss || null
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
        battery_storage: data.battery_storage,
        mount_type: data.mount_type,
        dc_wiring_loss: data.dc_wiring_loss,
        ac_wiring_loss: data.ac_wiring_loss,
        medium_voltage_loss: data.medium_voltage_loss,
        mv_line_loss: data.mv_line_loss
      });
    }, [data, reset]);

    const onSubmit: SubmitHandler<AssetOverviewFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateAssetOverviewDetails(data);
          notify(response.message || `Asset Overview information was successfully updated.`);
          reset({
            battery_storage: data.battery_storage,
            mount_type: data.mount_type,
            dc_wiring_loss: data.dc_wiring_loss,
            ac_wiring_loss: data.ac_wiring_loss,
            medium_voltage_loss: data.medium_voltage_loss,
            mv_line_loss: data.mv_line_loss
          });
          await queryClient.invalidateQueries({ queryKey: ['sites'] });
          setMode('view');
        } catch (e: any) {
          notify(e.response?.data?.message || 'Something went wrong when updating the Asset Overview information...');
        }
      },
      [notify, queryClient, reset, setMode, updateAssetOverviewDetails]
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
                <TextBox fieldName>Module Quantity:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.module_quantity}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Inverter Quantity:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.inverter_quantity}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Project Type:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.project_type}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>DC Ohmic Wiring Loss, %</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.dc_wiring_loss !== null ? formatFloatValue(data.dc_wiring_loss) : ''}</TextBox>
                ) : (
                  <Controller
                    name="dc_wiring_loss"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return 'DC Ohmic Wiring Loss is required field.';
                        if ((value as unknown as string).length > 100)
                          return 'DC Ohmic Wiring Loss length should not exceed 100 characters.';
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for DC Ohmic Wiring Loss'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.dc_wiring_loss}
                        multiline
                        required
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          inputComponent: FormattedNumericInputWithMinus as any,
                          ref: ref,
                          sx: inputStyles
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            {errors.dc_wiring_loss?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.dc_wiring_loss?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>AC Ohmic Wiring Loss, %</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.ac_wiring_loss !== null ? formatFloatValue(data.ac_wiring_loss) : ''}</TextBox>
                ) : (
                  <Controller
                    name="ac_wiring_loss"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return 'AC Ohmic Wiring Loss is required field.';
                        if ((value as unknown as string).length > 100)
                          return 'AC Ohmic Wiring Loss length should not exceed 100 characters.';
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for AC Ohmic Wiring Loss'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.ac_wiring_loss}
                        multiline
                        required
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          inputComponent: FormattedNumericInputWithMinus as any,
                          ref: ref,
                          sx: inputStyles
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            {errors.ac_wiring_loss?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.ac_wiring_loss?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Medium Voltage Transfo Loss, %</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>
                    {data.medium_voltage_loss !== null ? formatFloatValue(data.medium_voltage_loss) : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="medium_voltage_loss"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return 'Medium Voltage Transfo Loss is required field.';
                        if ((value as unknown as string).length > 100)
                          return 'Medium Voltage Transfo Loss length should not exceed 100 characters.';
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for Medium Voltage Transfo Loss'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.medium_voltage_loss}
                        multiline
                        required
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          inputComponent: FormattedNumericInputWithMinus as any,
                          ref: ref,
                          sx: inputStyles
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            {errors.medium_voltage_loss?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.medium_voltage_loss?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>MV Line Ohmic Loss, %</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.mv_line_loss !== null ? formatFloatValue(data.mv_line_loss) : ''}</TextBox>
                ) : (
                  <Controller
                    name="mv_line_loss"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return 'MV Line Ohmic Loss is required field.';
                        if ((value as unknown as string).length > 100)
                          return 'MV Line Ohmic Loss length should not exceed 100 characters.';
                        const withoutThousandSeparators = value.toString().replaceAll(',', '');
                        return Number.isNaN(Number.parseFloat(withoutThousandSeparators))
                          ? 'Invalid number provided as a value for MV Line Ohmic Loss'
                          : true;
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        placeholder=""
                        error={!!errors.mv_line_loss}
                        multiline
                        required
                        minRows={1}
                        maxRows={3}
                        disabled={isSubmitting}
                        inputRef={ref}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          inputComponent: FormattedNumericInputWithMinus as any,
                          ref: ref,
                          sx: inputStyles
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            {errors.mv_line_loss?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.mv_line_loss?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Mount Type:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.mount_type}</TextBox>
                ) : (
                  <Controller
                    name="mount_type"
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
                        {['Canopy', 'Carport', 'Dual Axis', 'Fixed Tilt', 'Single Axis'].map(status => (
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
            {errors.mount_type?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.mount_type?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Battery Storage:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{data.battery_storage || ''}</TextBox>
                ) : (
                  <Controller
                    name="battery_storage"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.battery_storage}
                        helperText={errors.battery_storage?.message}
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
        </Table>
      </Box>
    );
  }
);

AssetOverviewForm.displayName = 'AssetOverviewForm';

interface AssetOverviewCardProps {
  siteId: number;
  data: AssetOverviewCardData;
}

export const AssetOverviewCard: React.FC<AssetOverviewCardProps> = ({ siteId, data }) => (
  <InformationCardBase<AssetOverviewCardData>
    title="Asset Overview"
    informationCardData={data}
    siteId={siteId}
    InformationCardForm={AssetOverviewForm}
  />
);

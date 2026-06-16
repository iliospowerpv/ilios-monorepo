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
import { ProvenanceNote, BaselineNavLinks } from '../../provenance/BaselineProvenance';

type AssetOverviewCardData = Exclude<
  Awaited<ReturnType<typeof ApiClient.assetManagement.siteInfo>>['asset_overview'],
  null
>;

// Phase 1+2: baseline-driving fields (module/inverter quantities, project type and
// the four ohmic-loss values) are read-only and managed through the Data Room /
// project-facts promotion workflow. Only ordinary metadata stays editable here.
type AssetOverviewFormFields = Pick<AssetOverviewCardData, 'battery_storage' | 'mount_type'>;

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
        mount_type: data.mount_type
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
            mount_type: attributes.mount_type || null
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
        mount_type: data.mount_type
      });
    }, [data, reset]);

    const onSubmit: SubmitHandler<AssetOverviewFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateAssetOverviewDetails(data);
          notify(response.message || `Asset Overview information was successfully updated.`);
          reset({
            battery_storage: data.battery_storage,
            mount_type: data.mount_type
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
              <FieldCell mode={mode} fieldName component="th" scope="row" align="right">
                <TextBox>{data.module_quantity}</TextBox>
                <ProvenanceNote variant="source" />
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Inverter Quantity:</TextBox>
              </FieldCell>
              <FieldCell mode={mode} fieldName component="th" scope="row" align="right">
                <TextBox>{data.inverter_quantity}</TextBox>
                <ProvenanceNote variant="source" />
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Project Type:</TextBox>
              </FieldCell>
              <FieldCell mode={mode} fieldName component="th" scope="row" align="right">
                <TextBox>{data.project_type}</TextBox>
                <ProvenanceNote variant="source" />
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>DC Ohmic Wiring Loss, %</TextBox>
              </FieldCell>
              <FieldCell mode={mode} fieldName component="th" scope="row" align="right">
                <TextBox>{data.dc_wiring_loss !== null ? formatFloatValue(data.dc_wiring_loss) : ''}</TextBox>
                <ProvenanceNote variant="baseline" />
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>AC Ohmic Wiring Loss, %</TextBox>
              </FieldCell>
              <FieldCell mode={mode} fieldName component="th" scope="row" align="right">
                <TextBox>{data.ac_wiring_loss !== null ? formatFloatValue(data.ac_wiring_loss) : ''}</TextBox>
                <ProvenanceNote variant="baseline" />
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Medium Voltage Transfo Loss, %</TextBox>
              </FieldCell>
              <FieldCell mode={mode} fieldName component="th" scope="row" align="right">
                <TextBox>{data.medium_voltage_loss !== null ? formatFloatValue(data.medium_voltage_loss) : ''}</TextBox>
                <ProvenanceNote variant="baseline" />
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>MV Line Ohmic Loss, %</TextBox>
              </FieldCell>
              <FieldCell mode={mode} fieldName component="th" scope="row" align="right">
                <TextBox>{data.mv_line_loss !== null ? formatFloatValue(data.mv_line_loss) : ''}</TextBox>
                <ProvenanceNote variant="baseline" />
              </FieldCell>
            </TableRow>
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
        <BaselineNavLinks siteId={siteId} />
      </Box>
    );
  }
);

AssetOverviewForm.displayName = 'AssetOverviewForm';

interface AssetOverviewCardProps {
  siteId: number;
  data: AssetOverviewCardData;
  hideHeader?: boolean;
}

export const AssetOverviewCard: React.FC<AssetOverviewCardProps> = ({ siteId, data, hideHeader }) => (
  <InformationCardBase<AssetOverviewCardData>
    title="Asset Overview"
    informationCardData={data}
    siteId={siteId}
    InformationCardForm={AssetOverviewForm}
    hideHeader={hideHeader}
  />
);

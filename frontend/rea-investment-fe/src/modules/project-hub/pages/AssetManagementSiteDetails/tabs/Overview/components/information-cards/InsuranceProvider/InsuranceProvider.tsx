import React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
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
import FormHelperText from '@mui/material/FormHelperText';
import { EntityPicker } from '../../../../../../../../../components/common/EntityPicker/EntityPicker';
import type { EntityRelationship } from '../../../../../../../../../api/entities';

type InsuranceProviderCardData = Exclude<
  Awaited<ReturnType<typeof ApiClient.assetManagement.siteInfo>>['insurance_provider'],
  null
>;

type InsuranceProviderFormFields = Pick<InsuranceProviderCardData, 'insurance_address' | 'insurance_provider'>;

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

const ENTITY_ROLE = 'insurance_provider' as const;

const InsuranceProviderForm = React.forwardRef<
  InformationCardFormRef,
  InformationCardFormProps<InsuranceProviderCardData>
>(({ mode, setMode, siteId, data, reflectFormState, portfolioId }, ref) => {
  const queryClient = useQueryClient();
  const notify = useNotify();

  const [selectedEntityId, setSelectedEntityId] = React.useState<number | null>(null);
  const [existingRelationship, setExistingRelationship] = React.useState<EntityRelationship | null>(null);

  const { data: relationships } = useQuery({
    queryKey: ['entity-relationships', siteId],
    queryFn: () => ApiClient.entityRelationships.list(siteId),
    enabled: !!siteId
  });

  React.useEffect(() => {
    if (relationships?.items) {
      const rel = relationships.items.find(r => r.role === ENTITY_ROLE);
      if (rel) {
        setExistingRelationship(rel);
        setSelectedEntityId(rel.entity_id);
      }
    }
  }, [relationships]);

  const handleEntityChange = React.useCallback((_entityId: number | null) => {
    setSelectedEntityId(_entityId);
  }, []);

  const saveEntityRelationship = React.useCallback(async () => {
    if (!selectedEntityId) return;
    try {
      if (existingRelationship) {
        await ApiClient.entityRelationships.update(siteId, existingRelationship.id, {
          entity_id: selectedEntityId,
          role: ENTITY_ROLE
        });
      } else {
        await ApiClient.entityRelationships.create(siteId, {
          entity_id: selectedEntityId,
          role: ENTITY_ROLE
        });
      }
      queryClient.invalidateQueries({ queryKey: ['entity-relationships', siteId] });
    } catch {
      /* entity save non-blocking */
    }
  }, [selectedEntityId, existingRelationship, siteId, queryClient]);

  const { handleSubmit, formState, control, reset } = useForm<InsuranceProviderFormFields>({
    mode: 'onChange',
    criteriaMode: 'all',
    reValidateMode: 'onChange',
    defaultValues: {
      insurance_address: data.insurance_address || null,
      insurance_provider: data.insurance_provider || null
    }
  });

  const { errors, isValid, isSubmitting, isDirty } = formState;
  const { mutateAsync: updateInsuranceProviderDetails } = useMutation({
    mutationFn: (attributes: InsuranceProviderFormFields) =>
      ApiClient.assetManagement.updateSiteInfo({
        siteId,
        section: 'insurance_provider',
        data: {
          insurance_address: attributes.insurance_address || null,
          insurance_provider: attributes.insurance_provider || null
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
      insurance_address: data.insurance_address || null,
      insurance_provider: data.insurance_provider || null
    });
  }, [data, reset]);

  const onSubmit: SubmitHandler<InsuranceProviderFormFields> = React.useCallback(
    async data => {
      try {
        const response = await updateInsuranceProviderDetails(data);
        await saveEntityRelationship();
        notify(response.message || `Insurance provider information was successfully updated.`);
        reset(data);
        await queryClient.invalidateQueries({ queryKey: ['sites'] });
        setMode('view');
      } catch (e: any) {
        notify(e.response?.data?.message || 'Something went wrong when updating the Insurance Provider information...');
      }
    },
    [notify, queryClient, reset, setMode, updateInsuranceProviderDetails, saveEntityRelationship]
  );

  const handleFormSubmit = React.useMemo(() => handleSubmit(onSubmit), [handleSubmit, onSubmit]);

  React.useImperativeHandle(
    ref,
    () => ({
      resetForm: () => {
        reset();
        if (existingRelationship) {
          setSelectedEntityId(existingRelationship.entity_id);
        } else {
          setSelectedEntityId(null);
        }
      },
      submit: () => {
        handleFormSubmit();
      }
    }),
    [reset, handleFormSubmit, existingRelationship]
  );

  return (
    <Box component="form">
      <Table sx={{ width: '100%', height: 'auto', tableLayout: 'fixed' }} size="small">
        <TableBody>
          <TableRow>
            <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
              <TextBox fieldName>Entity:</TextBox>
            </FieldCell>
            <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
              {mode === 'view' ? (
                <TextBox>{existingRelationship?.entity_name || ''}</TextBox>
              ) : portfolioId ? (
                <EntityPicker
                  portfolioId={portfolioId}
                  entityType="insurance"
                  value={selectedEntityId}
                  onChange={handleEntityChange}
                  label="Insurance Entity"
                  role={ENTITY_ROLE}
                  size="small"
                />
              ) : null}
            </FieldCell>
          </TableRow>
          <TableRow>
            <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
              <TextBox fieldName>Provider:</TextBox>
            </FieldCell>
            <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
              {mode === 'view' ? (
                <TextBox>{data.insurance_provider}</TextBox>
              ) : (
                <Controller
                  name="insurance_provider"
                  control={control}
                  rules={{
                    maxLength: {
                      value: 100,
                      message: 'Provider length should not exceed 100 characters.'
                    }
                  }}
                  render={({ field: { ref, value, onChange, ...field } }) => (
                    <TextField
                      {...field}
                      fullWidth
                      size="small"
                      placeholder=""
                      error={!!errors.insurance_provider}
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
          {errors.insurance_provider?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.insurance_provider?.message}
                  </FormHelperText>
                </TextBox>
              </FieldCell>
            </TableRow>
          )}
          <TableRow>
            <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
              <TextBox fieldName>Address:</TextBox>
            </FieldCell>
            <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
              {mode === 'view' ? (
                <TextBox>{data.insurance_address}</TextBox>
              ) : (
                <Controller
                  name="insurance_address"
                  control={control}
                  rules={{
                    maxLength: {
                      value: 100,
                      message: 'Address length should not exceed 100 characters.'
                    }
                  }}
                  render={({ field: { ref, value, onChange, ...field } }) => (
                    <TextField
                      {...field}
                      fullWidth
                      size="small"
                      placeholder=""
                      error={!!errors.insurance_address}
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
          {errors.insurance_address?.message && (
            <TableRow>
              <FieldCell component="th" scope="row" width="40%" />
              <FieldCell component="th" scope="row" align="right">
                <TextBox>
                  <FormHelperText sx={{ margin: 0 }} error>
                    {errors.insurance_address?.message}
                  </FormHelperText>
                </TextBox>
              </FieldCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </Box>
  );
});

InsuranceProviderForm.displayName = 'InsuranceProviderForm';

interface InsuranceProviderCardProps {
  siteId: number;
  data: InsuranceProviderCardData;
  hideHeader?: boolean;
  portfolioId?: number;
}

export const InsuranceProviderCard: React.FC<InsuranceProviderCardProps> = ({
  siteId,
  data,
  hideHeader,
  portfolioId
}) => (
  <InformationCardBase<InsuranceProviderCardData>
    title="Insurance Provider"
    informationCardData={data}
    siteId={siteId}
    InformationCardForm={InsuranceProviderForm}
    hideHeader={hideHeader}
    portfolioId={portfolioId}
  />
);

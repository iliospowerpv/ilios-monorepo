import React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
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
import formatPhoneNumber from '../../../../../../../../../utils/formatters/formatPhoneNumber';
import { EntityPicker } from '../../../../../../../../../components/common/EntityPicker/EntityPicker';
import type { EntityRelationship, ProjectEntity } from '../../../../../../../../../api/entities';
import { EntityContactPicker } from '../../../../../../../../../components/common/EntityContactPicker/EntityContactPicker';
import type { Contact } from '../../../../../../../../../api/contacts';

type EPCContractorCardData = Awaited<ReturnType<typeof ApiClient.assetManagement.siteInfo>>['epc_contractor'];

type EPCContractorFormFields = Omit<EPCContractorCardData, 'provider' | 'agreement_effective_date'>;

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

const ENTITY_ROLE = 'epc_contractor' as const;

const EPCContractorForm = React.forwardRef<InformationCardFormRef, InformationCardFormProps<EPCContractorCardData>>(
  ({ mode, setMode, siteId, data, reflectFormState, portfolioId }, ref) => {
    const queryClient = useQueryClient();
    const notify = useNotify();

    const [selectedEntityId, setSelectedEntityId] = React.useState<number | null>(null);
    const [selectedContactId, setSelectedContactId] = React.useState<number | null>(null);
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

    const { handleSubmit, formState, control, reset, setValue } = useForm<EPCContractorFormFields>({
      mode: 'onChange',
      criteriaMode: 'all',
      reValidateMode: 'onChange',
      defaultValues: {
        epc_address: data.epc_address || null,
        epc_contact_email: data.epc_contact_email || null,
        epc_contact_name: data.epc_contact_name || null,
        epc_contact_phone: data.epc_contact_phone || null
      }
    });

    const { errors, isValid, isSubmitting, isDirty } = formState;
    const { mutateAsync: updateEPCContractorDetails } = useMutation({
      mutationFn: (attributes: EPCContractorFormFields) =>
        ApiClient.assetManagement.updateSiteInfo({
          siteId,
          section: 'epc_contractor',
          data: {
            epc_address: attributes.epc_address || null,
            epc_contact_email: attributes.epc_contact_email || null,
            epc_contact_name: attributes.epc_contact_name || null,
            epc_contact_phone: attributes.epc_contact_phone || null
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
        epc_address: data.epc_address || null,
        epc_contact_email: data.epc_contact_email || null,
        epc_contact_name: data.epc_contact_name || null,
        epc_contact_phone: data.epc_contact_phone || null
      });
    }, [data, reset]);

    const handleEntityChange = React.useCallback(
      (_entityId: number | null, entity?: ProjectEntity | null) => {
        setSelectedEntityId(_entityId);
        setSelectedContactId(null);
        setValue('epc_contact_name', null, { shouldDirty: true });
        setValue('epc_contact_email', null, { shouldDirty: true });
        setValue('epc_contact_phone', null, { shouldDirty: true });
        if (entity) {
          setValue('epc_address', entity.address || null, { shouldDirty: true });
        }
      },
      [setValue]
    );

    const handleContactChange = React.useCallback(
      (_contactId: number | null, contact: Contact | null) => {
        setSelectedContactId(_contactId);
        if (contact) {
          const fullName = [contact.first_name, contact.last_name].filter(Boolean).join(' ');
          setValue('epc_contact_name', fullName || null, { shouldDirty: true });
          setValue('epc_contact_email', contact.email || null, { shouldDirty: true });
          setValue('epc_contact_phone', contact.phone || null, { shouldDirty: true });
        }
      },
      [setValue]
    );

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

    const onSubmit: SubmitHandler<EPCContractorFormFields> = React.useCallback(
      async data => {
        try {
          const response = await updateEPCContractorDetails(data);
          await saveEntityRelationship();
          notify(response.message || `EPC Contractor information was successfully updated.`);
          reset({
            epc_address: data.epc_address,
            epc_contact_email: data.epc_contact_email,
            epc_contact_name: data.epc_contact_name,
            epc_contact_phone: data.epc_contact_phone
          });
          queryClient.invalidateQueries({ queryKey: ['sites'] });
          setMode('view');
        } catch (e: any) {
          notify(e.response?.data?.message || 'Something went wrong when updating the EPC Contractor information...');
        }
      },
      [notify, queryClient, reset, setMode, updateEPCContractorDetails, saveEntityRelationship]
    );

    const handleFormSubmit = React.useMemo(() => handleSubmit(onSubmit), [handleSubmit, onSubmit]);

    React.useImperativeHandle(
      ref,
      () => ({
        resetForm: () => {
          reset();
          setSelectedContactId(null);
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
                    entityType="epc_contractor"
                    value={selectedEntityId}
                    onChange={handleEntityChange}
                    label="EPC Contractor Entity"
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
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.provider}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Address:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.epc_address}</TextBox>
                ) : (
                  <Controller
                    name="epc_address"
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
                        error={!!errors.epc_address}
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
            {errors.epc_address?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.epc_address?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Contact:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{data.epc_contact_name}</TextBox>
                ) : portfolioId ? (
                  <EntityContactPicker
                    entityId={selectedEntityId}
                    portfolioId={portfolioId}
                    value={selectedContactId}
                    onChange={handleContactChange}
                    label="Contact"
                    disabled={!selectedEntityId}
                    size="small"
                  />
                ) : null}
              </FieldCell>
            </TableRow>
            {mode === 'view' && (
              <TableRow>
                <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                  <TextBox fieldName>Contact Email:</TextBox>
                </FieldCell>
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>{data.epc_contact_email}</TextBox>
                </FieldCell>
              </TableRow>
            )}
            {mode === 'view' && (
              <TableRow>
                <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                  <TextBox fieldName>Contact Phone #:</TextBox>
                </FieldCell>
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>{formatPhoneNumber(data.epc_contact_phone)}</TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell mode={mode} fieldName component="th" scope="row" width="40%">
                <TextBox fieldName>Agreement Effective Date:</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{data.agreement_effective_date}</TextBox>
              </FieldCell>
            </TableRow>
          </TableBody>
        </Table>
      </Box>
    );
  }
);

EPCContractorForm.displayName = 'EPCContractorForm';

interface EPCContractorCardProps {
  siteId: number;
  data: EPCContractorCardData;
  hideHeader?: boolean;
  portfolioId?: number;
}

export const EPCContractorCard: React.FC<EPCContractorCardProps> = ({ siteId, data, hideHeader, portfolioId }) => (
  <InformationCardBase<EPCContractorCardData>
    title="EPC Contractor"
    informationCardData={data}
    siteId={siteId}
    InformationCardForm={EPCContractorForm}
    hideHeader={hideHeader}
    portfolioId={portfolioId}
  />
);

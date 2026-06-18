import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm, useWatch } from 'react-hook-form';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import Collapse from '@mui/material/Collapse';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';

import { useNotify } from '../../../../../contexts/notifications/notifications';
import { ApiClient } from '../../../../../api';
import { usePrevious } from '../../../../../hooks/common/usePrevious';

type DocumentTermUserInputFormFields = {
  text: string;
  overrideNotes: string;
};

type SetDocumentKeyValueFn = typeof ApiClient.dueDiligence.setDocumentKeyValue;
type SetDocumentKeyValueParams = Parameters<SetDocumentKeyValueFn>[number]['params'];

export type DocumentTermUserInputFormSubmitHandler = SubmitHandler<DocumentTermUserInputFormFields>;

export interface DocumentTermUserInputFieldProps {
  text: string | null;
  siteId: number;
  documentId: number;
  termKey: string;
  isBaselineDriving?: boolean;
  aiValue?: string | null;
  // Fired after a value is successfully accepted/overridden so the parent can
  // refresh promotion eligibility (accepting a value creates a candidate fact).
  onValuePersisted?: () => void;
}

export interface DocumentTermUserInputFieldRef {
  setValue: (text: string) => void;
}

export const DocumentTermUserInputField = React.forwardRef<
  DocumentTermUserInputFieldRef,
  DocumentTermUserInputFieldProps
>((props, ref) => {
  const { text, siteId, documentId, termKey, isBaselineDriving = false, aiValue = null, onValuePersisted } = props;
  const notify = useNotify();
  const queryClient = useQueryClient();
  const MAX_LENGTH = 2000;
  const NOTES_MAX_LENGTH = 2000;

  const { handleSubmit, formState, control, reset, setValue, trigger } = useForm<DocumentTermUserInputFormFields>({
    mode: 'onChange',
    criteriaMode: 'all',
    reValidateMode: 'onChange',
    defaultValues: { text: text || '', overrideNotes: '' }
  });

  const watchedText = useWatch({ control, name: 'text' });
  // A baseline-driving field whose value differs from the AI-extracted value is an
  // "override". The server enforces a rationale for these (DD V2 Phase 1D); we collect
  // it here so the save succeeds and the reviewer's reasoning is captured.
  const requiresRationale =
    isBaselineDriving && (watchedText ?? '').trim().length > 0 && (watchedText ?? '').trim() !== (aiValue ?? '').trim();

  const { mutateAsync: updateDocumentKeyValue } = useMutation({
    mutationFn: (params: SetDocumentKeyValueParams) =>
      ApiClient.dueDiligence.setDocumentKeyValue({ siteId, documentId, params })
  });

  const onSubmit: DocumentTermUserInputFormSubmitHandler = async data => {
    try {
      const params: SetDocumentKeyValueParams = requiresRationale
        ? {
            name: termKey,
            value: data.text,
            status: 'overridden',
            override_value: data.text,
            override_notes: data.overrideNotes.trim()
          }
        : { name: termKey, value: data.text };
      const response = await updateDocumentKeyValue(params);
      reset({ text: data.text, overrideNotes: '' });
      queryClient.invalidateQueries({ queryKey: ['document-terms'] });
      onValuePersisted?.();
      notify(response.message || `Document key has been successfully updated.`);
    } catch (e: any) {
      notify(e.response?.data?.message || 'Something went wrong when updating a document key...');
    }
  };

  const { errors, isValid, isSubmitting, isDirty } = formState;
  const previousText = usePrevious(text);

  React.useImperativeHandle(
    ref,
    () => ({
      setValue: (text: string) => {
        setValue('text', text, { shouldDirty: true, shouldTouch: true, shouldValidate: true });
      }
    }),
    [setValue]
  );

  React.useEffect(() => {
    if (!isDirty && previousText !== text) {
      reset({ text: text || '', overrideNotes: '' });
    }
  }, [text, reset, isDirty, previousText]);

  // Re-validate the rationale field whenever the override requirement toggles so the
  // Save button's enabled state stays in sync with the edited value.
  React.useEffect(() => {
    trigger('overrideNotes');
  }, [requiresRationale, trigger]);

  const handleCancelClick = () => {
    reset({ text: text || '', overrideNotes: '' });
  };

  return (
    <Box pl="12px" component="form" onSubmit={handleSubmit(onSubmit)}>
      <Typography variant="h6" fontSize="16px" fontWeight="600" py="8px">
        Accepted Value
      </Typography>
      <Controller
        name="text"
        control={control}
        rules={{
          required: `Value length should be between 1 and ${MAX_LENGTH} characters.`,
          minLength: {
            value: 1,
            message: `Value length should be between 1 and ${MAX_LENGTH} characters.`
          },
          maxLength: {
            value: MAX_LENGTH,
            message: `Value length should not exceed the limit of ${MAX_LENGTH} characters.`
          }
        }}
        render={({ field: { ref, value, onChange, onBlur, ...field } }) => (
          <TextField
            {...field}
            fullWidth
            placeholder="Provide the value"
            helperText={errors.text?.message}
            error={!!errors.text}
            multiline
            minRows={1}
            maxRows={5}
            disabled={isSubmitting}
            inputRef={ref}
            value={value.trim().length ? value : ''}
            onBlur={onBlur}
            onChange={e => onChange(e.target.value || '')}
            InputProps={{
              sx: { '& > textarea::placeholder': { fontStyle: 'italic' } }
            }}
          />
        )}
      />
      <Collapse in={requiresRationale && isDirty}>
        <Typography variant="body2" color="text.secondary" pt="8px">
          This field feeds the production baseline. Overriding the AI-extracted value requires a rationale.
        </Typography>
        <Controller
          name="overrideNotes"
          control={control}
          rules={{
            validate: value =>
              !requiresRationale ||
              (!!value && value.trim().length > 0) ||
              'A rationale is required when overriding a baseline-driving field.',
            maxLength: {
              value: NOTES_MAX_LENGTH,
              message: `Rationale should not exceed the limit of ${NOTES_MAX_LENGTH} characters.`
            }
          }}
          render={({ field: { ref, onChange, ...field } }) => (
            <TextField
              {...field}
              fullWidth
              placeholder="Explain why you are overriding the extracted value"
              helperText={errors.overrideNotes?.message}
              error={!!errors.overrideNotes}
              multiline
              minRows={2}
              maxRows={5}
              disabled={isSubmitting}
              inputRef={ref}
              onChange={e => onChange(e.target.value || '')}
              sx={{ mt: '8px' }}
            />
          )}
        />
      </Collapse>
      <Collapse in={isDirty}>
        <Stack direction="row" width="100%" pt="10px" spacing={1} justifyContent="flex-end">
          <Button disabled={!isValid || !isDirty || isSubmitting} variant="contained" size="small" type="submit">
            Save
          </Button>
          <Button variant="outlined" size="small" onClick={handleCancelClick}>
            Cancel
          </Button>
        </Stack>
      </Collapse>
    </Box>
  );
});

DocumentTermUserInputField.displayName = 'DocumentTermUserInputField';

export default DocumentTermUserInputField;

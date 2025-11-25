import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import Collapse from '@mui/material/Collapse';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';

import { useNotify } from '../../../../../contexts/notifications/notifications';
import { ApiClient } from '../../../../../api';
import { usePrevious } from '../../../../../hooks/common/usePrevious';

type DocumentTermUserInputFormFields = {
  text: string;
};

type SetDocumentKeyValueFn = typeof ApiClient.dueDiligence.setDocumentKeyValue;
type SetDocumentKeyValueParams = Parameters<SetDocumentKeyValueFn>[number]['params'];

export type DocumentTermUserInputFormSubmitHandler = SubmitHandler<DocumentTermUserInputFormFields>;

export interface DocumentTermUserInputFieldProps {
  text: string | null;
  siteId: number;
  documentId: number;
  termKey: string;
}

export interface DocumentTermUserInputFieldRef {
  setValue: (text: string) => void;
}

export const DocumentTermUserInputField = React.forwardRef<
  DocumentTermUserInputFieldRef,
  DocumentTermUserInputFieldProps
>((props, ref) => {
  const { text, siteId, documentId, termKey } = props;
  const notify = useNotify();
  const queryClient = useQueryClient();
  const MAX_LENGTH = 2000;

  const { handleSubmit, formState, control, reset, setValue } = useForm<DocumentTermUserInputFormFields>({
    mode: 'onChange',
    criteriaMode: 'all',
    reValidateMode: 'onChange',
    defaultValues: { text: text || '' }
  });

  const { mutateAsync: updateDocumentKeyValue } = useMutation({
    mutationFn: (params: SetDocumentKeyValueParams) =>
      ApiClient.dueDiligence.setDocumentKeyValue({ siteId, documentId, params })
  });

  const onSubmit: DocumentTermUserInputFormSubmitHandler = async data => {
    try {
      const response = await updateDocumentKeyValue({
        name: termKey,
        value: data.text
      });
      reset({ text: data.text });
      queryClient.invalidateQueries({ queryKey: ['document-terms'] });
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
      reset({ text: text || '' });
    }
  }, [text, reset, isDirty, previousText]);

  const handleCancelClick = () => {
    reset({ text: text || '' });
  };

  return (
    <Box pl="12px" component="form" onSubmit={handleSubmit(onSubmit)}>
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

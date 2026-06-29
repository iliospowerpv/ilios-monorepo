import React, { useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import Typography from '@mui/material/Typography';
import { SearchableSelect } from '../SearchableSelect/SearchableSelect';
import type { WorkflowStepSchema, WorkflowFieldSchema } from './types';

type StepFormValues = Record<string, string>;

interface WizardStepFieldsProps {
  step: WorkflowStepSchema;
  initialValues: Record<string, unknown>;
  saving: boolean;
  serverErrors: Record<string, string> | null;
  onSubmit: (values: StepFormValues) => void;
  onExit: () => void;
}

function buildDefaults(step: WorkflowStepSchema, initialValues: Record<string, unknown>): StepFormValues {
  const defaults: StepFormValues = {};
  step.inputs.forEach(field => {
    const value = initialValues[field.name];
    defaults[field.name] = value === undefined || value === null ? '' : String(value);
  });
  return defaults;
}

function buildRules(field: WorkflowFieldSchema) {
  const rules: Record<string, unknown> = {};
  if (field.required) {
    rules.required = `${field.label} is required`;
  }
  if (field.max_length) {
    rules.maxLength = { value: field.max_length, message: `Must be at most ${field.max_length} characters` };
  }
  if (field.type === 'email') {
    rules.pattern = { value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: 'Enter a valid email address' };
  } else if (field.pattern) {
    rules.pattern = { value: new RegExp(field.pattern), message: 'Please use a valid format' };
  }
  return rules;
}

export const WizardStepFields: React.FC<WizardStepFieldsProps> = ({
  step,
  initialValues,
  saving,
  serverErrors,
  onSubmit,
  onExit
}) => {
  const {
    control,
    register,
    handleSubmit,
    setError,
    formState: { errors }
  } = useForm<StepFormValues>({
    defaultValues: buildDefaults(step, initialValues),
    mode: 'onBlur'
  });

  // Apply server-side field validation onto the form when a save returns invalid.
  useEffect(() => {
    if (!serverErrors) return;
    const known = new Set(step.inputs.map(field => field.name));
    Object.entries(serverErrors).forEach(([key, message]) => {
      if (known.has(key)) {
        setError(key, { type: 'server', message });
      }
    });
  }, [serverErrors, setError, step.inputs]);

  // Any server error that doesn't map to a rendered field is shown as a banner.
  const rootError = serverErrors
    ? (serverErrors._ ??
        Object.entries(serverErrors)
          .filter(([key]) => !step.inputs.some(field => field.name === key))
          .map(([, message]) => message)[0])
    : undefined;

  const renderField = (field: WorkflowFieldSchema) => {
    const fieldError = errors[field.name];
    const helperText = fieldError ? String(fieldError.message ?? '') : (field.help ?? undefined);
    const rules = buildRules(field);

    if (field.type === 'select') {
      return (
        <Controller
          key={field.name}
          name={field.name}
          control={control}
          rules={rules}
          render={({ field: ctl }) => (
            <SearchableSelect
              label={field.label}
              required={field.required}
              options={(field.options ?? []).map(option => ({ label: option.label, value: option.value }))}
              value={(ctl.value as string) || ''}
              onChange={value => ctl.onChange(value)}
              onBlur={ctl.onBlur}
              error={!!fieldError}
              helperText={helperText}
              placeholder={field.placeholder ?? undefined}
            />
          )}
        />
      );
    }

    const multiline = field.type === 'textarea';
    const inputType = field.type === 'email' ? 'email' : field.type === 'tel' ? 'tel' : 'text';

    return (
      <TextField
        key={field.name}
        label={field.label}
        required={field.required}
        type={inputType}
        multiline={multiline}
        minRows={multiline ? 3 : undefined}
        fullWidth
        placeholder={field.placeholder ?? undefined}
        error={!!fieldError}
        helperText={helperText}
        inputProps={{ maxLength: field.max_length ?? undefined }}
        {...register(field.name, rules)}
      />
    );
  };

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
      {step.help && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {step.help}
        </Typography>
      )}
      {rootError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {rootError}
        </Alert>
      )}
      <Stack spacing={2.5}>{step.inputs.map(renderField)}</Stack>
      <Stack direction="row" justifyContent="space-between" sx={{ mt: 4 }}>
        <Button variant="text" color="inherit" onClick={onExit} disabled={saving}>
          Cancel
        </Button>
        <Button type="submit" variant="contained" disabled={saving}>
          {saving ? 'Saving…' : 'Next'}
        </Button>
      </Stack>
    </Box>
  );
};

export default WizardStepFields;

import React from 'react';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

interface CredentialFieldDef {
  key: string;
  label: string;
  required: boolean;
  helperText?: string;
}

interface CredentialFieldsFormProps {
  providerKey: string;
  configSchema: Record<string, unknown> | null | undefined;
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
  disabled?: boolean;
}

const FALLBACK_FIELDS: Record<string, CredentialFieldDef[]> = {
  also_energy: [
    { key: 'username', label: 'Username', required: true },
    { key: 'password', label: 'Password', required: true }
  ],
  kmc: [{ key: 'token', label: 'API Token', required: true }]
};

const DEFAULT_FIELDS: CredentialFieldDef[] = [{ key: 'token', label: 'Token / Secret', required: true }];

const fieldsFromSchema = (schema: Record<string, unknown> | null | undefined): CredentialFieldDef[] => {
  if (!schema || typeof schema !== 'object') return [];
  const credSchema = (schema as Record<string, unknown>).credential_schema;
  if (!credSchema || typeof credSchema !== 'object') return [];
  const props = (credSchema as Record<string, unknown>).properties;
  const requiredList = Array.isArray((credSchema as Record<string, unknown>).required)
    ? ((credSchema as Record<string, unknown>).required as string[])
    : [];
  if (!props || typeof props !== 'object') return [];
  return Object.entries(props as Record<string, unknown>).map(([key, def]) => {
    const meta = (def && typeof def === 'object' ? (def as Record<string, unknown>) : {}) as Record<string, unknown>;
    return {
      key,
      label: typeof meta.title === 'string' ? meta.title : key,
      required: requiredList.includes(key),
      helperText: typeof meta.description === 'string' ? meta.description : undefined
    };
  });
};

export const resolveCredentialFields = (
  providerKey: string,
  configSchema: Record<string, unknown> | null | undefined
): CredentialFieldDef[] => {
  const fromSchema = fieldsFromSchema(configSchema);
  if (fromSchema.length > 0) return fromSchema;
  return FALLBACK_FIELDS[providerKey] ?? DEFAULT_FIELDS;
};

export const CredentialFieldsForm: React.FC<CredentialFieldsFormProps> = ({
  providerKey,
  configSchema,
  values,
  onChange,
  disabled
}) => {
  const fields = React.useMemo(() => resolveCredentialFields(providerKey, configSchema), [providerKey, configSchema]);

  if (fields.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No credential fields are configured for this provider.
      </Typography>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {fields.map(field => (
        <TextField
          key={field.key}
          label={field.label + (field.required ? ' *' : '')}
          value={values[field.key] ?? ''}
          onChange={e => onChange(field.key, e.target.value)}
          type="password"
          fullWidth
          autoComplete="new-password"
          disabled={disabled}
          helperText={field.helperText}
          inputProps={{
            autoCorrect: 'off',
            autoCapitalize: 'off',
            spellCheck: 'false'
          }}
        />
      ))}
      <Typography variant="caption" color="text.secondary">
        Credentials are stored write-only. They are never displayed back in this UI after save.
      </Typography>
    </Box>
  );
};

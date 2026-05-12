import React from 'react';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import InputAdornment from '@mui/material/InputAdornment';
import TextField from '@mui/material/TextField';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined';
import VisibilityOffOutlinedIcon from '@mui/icons-material/VisibilityOffOutlined';

interface CredentialFieldDef {
  key: string;
  label: string;
  required: boolean;
  helperText?: string;
  /** True when the value is a secret (password / token / api key) and should
   *  be masked by default with a show/hide toggle. False for usernames,
   *  emails, account ids and other non-secret identifiers. */
  isSecret: boolean;
}

interface CredentialFieldsFormProps {
  providerKey: string;
  configSchema: Record<string, unknown> | null | undefined;
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
  disabled?: boolean;
}

// Heuristic: treat a credential field as secret when its key looks like a
// password / token / secret / API key. Username, email, account-id and
// similar identifiers are not secret and should be visible while typing
// so the operator can confirm what they entered.
const SECRET_KEY_PATTERN = /(password|secret|token|api[_-]?key|apikey|private[_-]?key)/i;

const isSecretKey = (key: string): boolean => SECRET_KEY_PATTERN.test(key);

const FALLBACK_FIELDS: Record<string, Omit<CredentialFieldDef, 'isSecret'>[]> = {
  also_energy: [
    { key: 'username', label: 'Username', required: true },
    { key: 'password', label: 'Password', required: true }
  ],
  kmc: [{ key: 'token', label: 'API Token', required: true }]
};

const DEFAULT_FIELDS: Omit<CredentialFieldDef, 'isSecret'>[] = [
  { key: 'token', label: 'Token / Secret', required: true }
];

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
    // Allow the schema to override secrecy via `format: "password"` or
    // an explicit `x-secret: true`; fall back to the key heuristic.
    const formatHint = typeof meta.format === 'string' ? (meta.format as string).toLowerCase() : '';
    const explicitSecret = typeof meta['x-secret'] === 'boolean' ? (meta['x-secret'] as boolean) : null;
    const isSecret =
      explicitSecret !== null
        ? explicitSecret
        : formatHint === 'password' || formatHint === 'secret' || isSecretKey(key);
    return {
      key,
      label: typeof meta.title === 'string' ? meta.title : key,
      required: requiredList.includes(key),
      helperText: typeof meta.description === 'string' ? meta.description : undefined,
      isSecret
    };
  });
};

export const resolveCredentialFields = (
  providerKey: string,
  configSchema: Record<string, unknown> | null | undefined
): CredentialFieldDef[] => {
  const fromSchema = fieldsFromSchema(configSchema);
  if (fromSchema.length > 0) return fromSchema;
  const fallback = FALLBACK_FIELDS[providerKey] ?? DEFAULT_FIELDS;
  return fallback.map(field => ({ ...field, isSecret: isSecretKey(field.key) }));
};

export const CredentialFieldsForm: React.FC<CredentialFieldsFormProps> = ({
  providerKey,
  configSchema,
  values,
  onChange,
  disabled
}) => {
  const fields = React.useMemo(() => resolveCredentialFields(providerKey, configSchema), [providerKey, configSchema]);
  // Per-field reveal state for secret fields. Defaults to hidden; the
  // operator can click the eye icon to peek while typing/pasting.
  const [revealed, setRevealed] = React.useState<Record<string, boolean>>({});

  const toggleReveal = React.useCallback((key: string) => {
    setRevealed(prev => ({ ...prev, [key]: !prev[key] }));
  }, []);

  if (fields.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No credential fields are configured for this provider.
      </Typography>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {fields.map(field => {
        const isSecret = field.isSecret;
        const isRevealed = !!revealed[field.key];
        return (
          <TextField
            key={field.key}
            label={field.label + (field.required ? ' *' : '')}
            value={values[field.key] ?? ''}
            onChange={e => onChange(field.key, e.target.value)}
            type={isSecret && !isRevealed ? 'password' : 'text'}
            fullWidth
            autoComplete={isSecret ? 'new-password' : 'off'}
            disabled={disabled}
            helperText={field.helperText}
            inputProps={{
              autoCorrect: 'off',
              autoCapitalize: 'off',
              spellCheck: 'false'
            }}
            InputProps={
              isSecret
                ? {
                    endAdornment: (
                      <InputAdornment position="end">
                        <Tooltip title={isRevealed ? 'Hide' : 'Show'}>
                          <span>
                            <IconButton
                              aria-label={isRevealed ? `Hide ${field.label}` : `Show ${field.label}`}
                              edge="end"
                              size="small"
                              onClick={() => toggleReveal(field.key)}
                              disabled={disabled}
                            >
                              {isRevealed ? (
                                <VisibilityOffOutlinedIcon fontSize="small" />
                              ) : (
                                <VisibilityOutlinedIcon fontSize="small" />
                              )}
                            </IconButton>
                          </span>
                        </Tooltip>
                      </InputAdornment>
                    )
                  }
                : undefined
            }
          />
        );
      })}
      <Typography variant="caption" color="text.secondary">
        Credentials are stored write-only. They are never displayed back in this UI after save.
      </Typography>
    </Box>
  );
};

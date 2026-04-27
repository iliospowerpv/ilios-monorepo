import React from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CircularProgress from '@mui/material/CircularProgress';
import IconButton from '@mui/material/IconButton';
import Skeleton from '@mui/material/Skeleton';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import SensorsIcon from '@mui/icons-material/Sensors';

import type { LicensedProvider } from '../../../../../types/telemetryV2';
import { useLicensedProviders, useTelemetryAdminMutations } from '../../../../../hooks/telemetryV2';

interface LicensedProviderTypesPanelProps {
  companyId: number;
  canEdit: boolean;
  onAddLicense: () => void;
  onError: (message: string) => void;
}

export const LicensedProviderTypesPanel: React.FC<LicensedProviderTypesPanelProps> = ({
  companyId,
  canEdit,
  onAddLicense,
  onError
}) => {
  const { data, isLoading, error } = useLicensedProviders(companyId);
  const { revokeLicense } = useTelemetryAdminMutations(companyId);
  const [confirming, setConfirming] = React.useState<LicensedProvider | null>(null);

  const items = data?.items ?? [];

  const handleRevoke = (license: LicensedProvider) => {
    revokeLicense.mutate(license.id, {
      onSuccess: () => setConfirming(null),
      onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
        const message = err.response?.data?.detail || err.message || 'Failed to revoke license.';
        onError(message);
        setConfirming(null);
      }
    });
  };

  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="subtitle1" fontWeight={600}>
              Licensed Provider Types
            </Typography>
            <Chip size="small" label={`${items.length}`} variant="outlined" />
          </Box>
          {canEdit && (
            <Button size="small" variant="outlined" startIcon={<AddIcon />} onClick={onAddLicense}>
              Add Licensed Provider
            </Button>
          )}
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Telemetry provider types this company is allowed to use. Provider Accounts (below) must be created against a
          licensed provider type.
        </Typography>

        {isLoading ? (
          <Skeleton variant="rectangular" height={80} />
        ) : error ? (
          <Alert severity="error">Failed to load licensed providers.</Alert>
        ) : items.length === 0 ? (
          <Alert severity="info" icon={<SensorsIcon />}>
            No provider types are licensed for this company yet.
            {canEdit
              ? ' Click Add Licensed Provider to license one.'
              : ' Ask a telemetry administrator to license one.'}
          </Alert>
        ) : (
          <Stack spacing={1}>
            {items.map(license => {
              const isRevoking = revokeLicense.isPending && confirming?.id === license.id;
              const cannotRevoke = (license.account_count ?? 0) > 0;
              return (
                <Box
                  key={license.id}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2,
                    p: 1.5,
                    border: theme => `1px solid ${theme.palette.divider}`,
                    borderRadius: 1
                  }}
                >
                  <SensorsIcon color="primary" fontSize="small" />
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography variant="subtitle2">
                      {license.display_name}
                      <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                        ({license.provider_key})
                      </Typography>
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {license.account_count} account{license.account_count === 1 ? '' : 's'}
                      {license.status === 'suspended' && ' • License suspended'}
                    </Typography>
                  </Box>
                  {canEdit && (
                    <Tooltip
                      title={
                        cannotRevoke
                          ? `Cannot revoke — ${license.account_count} account${
                              license.account_count === 1 ? '' : 's'
                            } still use this provider. Archive those accounts first.`
                          : 'Revoke this license'
                      }
                    >
                      <span>
                        <IconButton
                          size="small"
                          color="error"
                          disabled={cannotRevoke || isRevoking}
                          onClick={() => {
                            setConfirming(license);
                            handleRevoke(license);
                          }}
                        >
                          {isRevoking ? (
                            <CircularProgress size={16} color="inherit" />
                          ) : (
                            <DeleteOutlineIcon fontSize="small" />
                          )}
                        </IconButton>
                      </span>
                    </Tooltip>
                  )}
                </Box>
              );
            })}
          </Stack>
        )}
      </CardContent>
    </Card>
  );
};

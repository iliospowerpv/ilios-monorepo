import React from 'react';
import Chip from '@mui/material/Chip';
import type { ChipProps } from '@mui/material/Chip';
import Tooltip from '@mui/material/Tooltip';

import type { CredentialStatus, LastSyncStatus, ProviderAccountStatus } from '../../../../../types/telemetryV2';

const lifecycleMeta: Record<ProviderAccountStatus, { label: string; color: ChipProps['color']; tooltip: string }> = {
  active: {
    label: 'Active',
    color: 'success',
    tooltip: 'Account is enabled and visible to project users.'
  },
  paused: {
    label: 'Paused',
    color: 'warning',
    tooltip: 'Account is paused. Sync and credential testing are blocked.'
  },
  archived: {
    label: 'Archived',
    color: 'default',
    tooltip: 'Account is archived (soft-deleted). Stored credentials are retained until an administrator purges them.'
  }
};

const credentialMeta: Record<CredentialStatus, { label: string; color: ChipProps['color']; tooltip: string }> = {
  unverified: {
    label: 'Not tested',
    color: 'warning',
    tooltip: 'Credentials have been saved but never verified. Click Test Credentials to verify.'
  },
  verified: {
    label: 'Verified',
    color: 'success',
    tooltip: 'Credentials succeeded on the most recent test.'
  },
  invalid: {
    label: 'Invalid',
    color: 'error',
    tooltip: 'Credentials failed on the most recent test. Rotate the credentials and test again before syncing.'
  },
  expired: {
    label: 'Expired',
    color: 'error',
    tooltip: 'Credentials are no longer accepted by the provider. Rotate the credentials and test again before syncing.'
  }
};

const syncMeta: Record<LastSyncStatus, { label: string; color: ChipProps['color']; tooltip: string }> = {
  never: {
    label: 'Never synced',
    color: 'default',
    tooltip: 'Sites have not been synced for this account yet.'
  },
  success: {
    label: 'Synced',
    color: 'success',
    tooltip: 'Most recent sync succeeded.'
  },
  partial: {
    label: 'Partial',
    color: 'warning',
    tooltip: 'Most recent sync completed with some sites missing.'
  },
  failed: {
    label: 'Sync failed',
    color: 'error',
    tooltip: 'Most recent sync failed. Inspect the account for the error message.'
  }
};

export const LifecycleChip: React.FC<{ value: ProviderAccountStatus; size?: ChipProps['size'] }> = ({
  value,
  size = 'small'
}) => {
  const meta = lifecycleMeta[value] ?? { label: value, color: 'default', tooltip: '' };
  return (
    <Tooltip title={meta.tooltip} arrow>
      <Chip size={size} color={meta.color} label={meta.label} variant="outlined" />
    </Tooltip>
  );
};

export const CredentialChip: React.FC<{ value: CredentialStatus; size?: ChipProps['size'] }> = ({
  value,
  size = 'small'
}) => {
  const meta = credentialMeta[value] ?? { label: value, color: 'default', tooltip: '' };
  return (
    <Tooltip title={meta.tooltip} arrow>
      <Chip size={size} color={meta.color} label={meta.label} variant="filled" />
    </Tooltip>
  );
};

export const SyncChip: React.FC<{ value: LastSyncStatus; size?: ChipProps['size'] }> = ({ value, size = 'small' }) => {
  const meta = syncMeta[value] ?? { label: value, color: 'default', tooltip: '' };
  return (
    <Tooltip title={meta.tooltip} arrow>
      <Chip size={size} color={meta.color} label={meta.label} variant="outlined" />
    </Tooltip>
  );
};

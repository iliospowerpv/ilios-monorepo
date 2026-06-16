import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Link from '@mui/material/Link';
import Tooltip from '@mui/material/Tooltip';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import FolderOutlinedIcon from '@mui/icons-material/FolderOutlined';
import FactCheckOutlinedIcon from '@mui/icons-material/FactCheckOutlined';

import { useAuth } from '../../../../../../../../contexts/auth/auth';

/**
 * Provenance + navigation helpers for Project Hub Overview cards.
 *
 * These are presentation-only affordances introduced in Phase 1+2 of the
 * Overview safe-labeling work. They communicate that certain Overview fields
 * are baseline-driving (managed through the Data Room / project-facts promotion
 * workflow) and therefore read-only here. They perform NO mutations and do NOT
 * read from project_facts (read rebinding is deferred to Phase 3).
 */

export type ProvenanceVariant = 'source' | 'baseline';

const PROVENANCE_LABELS: Record<ProvenanceVariant, string> = {
  source: 'Source: Data Room / promoted project facts',
  baseline: 'Baseline-driving — managed via Data Room'
};

const PROVENANCE_TOOLTIPS: Record<ProvenanceVariant, string> = {
  source:
    'This value is sourced from accepted Data Room documents and promoted project facts. Update it in the Data Room rather than here.',
  baseline:
    'This value drives expected-production baselines. It is managed through the Data Room and promotion workflow, so it is read-only on this card.'
};

/**
 * Small, muted inline note rendered beneath a read-only field value. Inherits
 * the surrounding cell text alignment (right in view mode, left in edit mode).
 */
export const ProvenanceNote: React.FC<{ variant: ProvenanceVariant }> = ({ variant }) => (
  <Box
    sx={{
      mt: '2px',
      color: 'text.secondary',
      fontSize: '0.6875rem',
      lineHeight: 1.3
    }}
  >
    <Tooltip title={PROVENANCE_TOOLTIPS[variant]} arrow placement="top">
      <Box
        component="span"
        sx={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '3px',
          verticalAlign: 'middle',
          cursor: 'help'
        }}
      >
        <LockOutlinedIcon sx={{ fontSize: '0.8125rem' }} />
        <span>{PROVENANCE_LABELS[variant]}</span>
      </Box>
    </Tooltip>
  </Box>
);

/**
 * Footer row of read-only navigation links pointing at the surfaces where
 * baseline-driving values are actually managed. No mutation buttons. The
 * Reconciliation link mirrors the page-level permission gate (system user OR
 * Diligence:view) so we never surface a link that lands on an access-restricted
 * view for users without diligence access.
 */
export const BaselineNavLinks: React.FC<{ siteId: number }> = ({ siteId }) => {
  const { user } = useAuth();
  const canViewReconciliation = !!user?.is_system_user || !!user?.role?.permissions?.['Diligence']?.view;

  return (
    <Stack
      direction="row"
      spacing={2}
      flexWrap="wrap"
      sx={{ mt: 1, px: '8px', color: 'text.secondary', fontSize: '0.75rem' }}
    >
      <Link
        component={RouterLink}
        to={`/project-hub/projects/${siteId}/data-room`}
        variant="caption"
        underline="hover"
        sx={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
      >
        <FolderOutlinedIcon sx={{ fontSize: '0.875rem' }} />
        Open Data Room
      </Link>
      {canViewReconciliation && (
        <Link
          component={RouterLink}
          to={`/project-hub/projects/${siteId}/reconciliation`}
          variant="caption"
          underline="hover"
          sx={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
        >
          <FactCheckOutlinedIcon sx={{ fontSize: '0.875rem' }} />
          View Reconciliation
        </Link>
      )}
    </Stack>
  );
};

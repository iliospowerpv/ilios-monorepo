import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Link from '@mui/material/Link';

interface BaselineInvalidBannerProps {
  // Site whose active baseline is physically invalid. Used to deep-link to the
  // Draft Baseline Review surface (Project Hub → Reconciliation) where a
  // source-backed replacement baseline is created/approved/activated.
  siteId: number;
  // The invalid active baseline's id (from the read-path `invalid_baseline_id`),
  // surfaced to the reviewer for context. Optional/no-op when absent.
  invalidBaselineId?: number | null;
  // Backend's human-readable reason the baseline failed fail-closed validation.
  // When absent, a generic message is shown.
  summary?: string | null;
  // Suggested next action from the read path; falls back to a default.
  requiredAction?: string | null;
}

/**
 * Honest "expected unavailable" banner shown when a site has an ACTIVE expected
 * baseline that failed fail-closed physics validation. Actuals stay visible; the
 * expected series/value is suppressed (never fabricated to 0). It deep-links to
 * the Draft Baseline Review flow so a reviewer can create a corrected,
 * source-backed replacement. It triggers no writes and never mutates the
 * invalid baseline.
 */
const BaselineInvalidBanner: React.FC<BaselineInvalidBannerProps> = ({
  siteId,
  invalidBaselineId,
  summary,
  requiredAction
}) => (
  <Alert severity="warning" sx={{ mt: '8px' }}>
    <AlertTitle>Expected comparison unavailable: active baseline requires replacement.</AlertTitle>
    {summary || 'The active expected baseline failed physics validation, so expected production is shown as N/A.'}
    {invalidBaselineId != null ? ` (Baseline #${invalidBaselineId}.)` : ''}{' '}
    {requiredAction || 'Create a corrected, source-backed replacement baseline to restore the expected comparison.'}{' '}
    <Link component={RouterLink} to={`/project-hub/projects/${siteId}/reconciliation`}>
      Open Draft Baseline Review
    </Link>
  </Alert>
);

export default BaselineInvalidBanner;

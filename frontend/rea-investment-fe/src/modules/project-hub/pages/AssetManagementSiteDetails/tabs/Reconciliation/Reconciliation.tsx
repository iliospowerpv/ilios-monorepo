import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import FormControlLabel from '@mui/material/FormControlLabel';
import Switch from '@mui/material/Switch';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import FactCheckOutlinedIcon from '@mui/icons-material/FactCheckOutlined';

import type { AssetManagementSiteDetailsTabProps } from '../types';
import { ApiClient } from '../../../../../../api';
import type { ReconciliationRow } from '../../../../../../api';
import { useAuth } from '../../../../../../contexts/auth/auth';
import ReadinessSummary from './components/ReadinessSummary';
import ReconciliationTable from './components/ReconciliationTable';
import { CATEGORY_ORDER, STATUS_META, categoryLabel, statusMeta, formatDateTime } from './utils';

const reconciliationQuery = (siteId: number, enabled: boolean) => ({
  queryKey: ['site', 'reconciliation', { siteId }],
  queryFn: () => ApiClient.reconciliation.getSiteReconciliation(siteId),
  enabled,
  retry: false as const
});

export const Reconciliation: React.FC<AssetManagementSiteDetailsTabProps> = ({ siteDetails }) => {
  const siteId = siteDetails?.id;
  const isValidId = Number.isSafeInteger(siteId) && siteId > 0;

  const { user } = useAuth();
  // Promote/Create-Task require Diligence edit rights (system users always pass).
  const canEdit = Boolean(user?.is_system_user) || Boolean(user?.role?.permissions?.Diligence?.edit);

  const { data, isLoading, error } = useQuery(reconciliationQuery(isValidId ? siteId : -1, isValidId));

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [warningsOnly, setWarningsOnly] = useState(false);

  const filteredRows = useMemo<ReconciliationRow[]>(() => {
    if (!data) return [];
    const term = search.trim().toLowerCase();
    return data.rows.filter(row => {
      if (statusFilter !== 'all' && row.status !== statusFilter) return false;
      if (categoryFilter !== 'all' && row.category !== categoryFilter) return false;
      if (warningsOnly && row.warnings.length === 0) return false;
      if (term) {
        const haystack = `${row.display_label} ${row.canonical_field}`.toLowerCase();
        if (!haystack.includes(term)) return false;
      }
      return true;
    });
  }, [data, search, statusFilter, categoryFilter, warningsOnly]);

  const statusOptions = useMemo(() => {
    const present = new Set((data?.rows ?? []).map(r => r.status));
    return Object.keys(STATUS_META).filter(s => present.has(s));
  }, [data]);

  const categoryOptions = useMemo(() => {
    const present = new Set((data?.rows ?? []).map(r => r.category));
    const known = CATEGORY_ORDER.filter(c => present.has(c));
    const extras = Array.from(present).filter(c => !CATEGORY_ORDER.includes(c));
    return [...known, ...extras];
  }, [data]);

  if (isLoading) {
    return (
      <Box display="flex" alignItems="center" justifyContent="center" py={6} data-testid="reconciliation-loading">
        <CircularProgress size={40} />
      </Box>
    );
  }

  if (error) {
    const status = (error as { response?: { status?: number } })?.response?.status;
    if (status === 401 || status === 403) {
      return (
        <Alert severity="warning" icon={<LockOutlinedIcon />} data-testid="reconciliation-unauthorized">
          <AlertTitle>Access restricted</AlertTitle>
          You don&apos;t have permission to view the assumptions reconciliation for this project. This view requires
          Diligence access.
        </Alert>
      );
    }
    return (
      <Alert severity="error" data-testid="reconciliation-error">
        <AlertTitle>Couldn&apos;t load reconciliation</AlertTitle>
        Something went wrong while loading the assumptions reconciliation. Please try again later.
      </Alert>
    );
  }

  if (!data) {
    return null;
  }

  const hasRows = data.rows.length > 0;

  return (
    <Box data-testid="reconciliation-tab">
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
        <FactCheckOutlinedIcon color="primary" />
        <Typography variant="h5" sx={{ fontWeight: 600 }}>
          Assumptions Reconciliation
        </Typography>
        {canEdit ? (
          <Chip
            icon={<FactCheckOutlinedIcon />}
            label="Promote enabled"
            color="primary"
            size="small"
            variant="outlined"
            sx={{ ml: 1 }}
          />
        ) : (
          <Chip icon={<LockOutlinedIcon />} label="Read-only" size="small" variant="outlined" sx={{ ml: 1 }} />
        )}
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {siteDetails.name} · Generated {formatDateTime(data.generated_at)}
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }} data-testid="reconciliation-disclaimer">
        <AlertTitle>How to read this view</AlertTitle>
        This is an audit of how source-backed diligence facts flow into current assumptions and baselines.{' '}
        {canEdit ? (
          <>
            Values are never edited, accepted, or overridden here — acceptance stays in the Data Room — and baselines
            are never activated here. The only actions available are <strong>Promote</strong> (move an already-accepted
            value to an active assumption — file-version-scoped and all-or-nothing, never a single field) and{' '}
            <strong>Create Task</strong> to hand a row off.
          </>
        ) : (
          <>It is strictly read-only — nothing here is edited, accepted, promoted, or activated.</>
        )}
        <Box component="ul" sx={{ pl: 3, mb: 0, mt: 1 }}>
          <li>
            <strong>AI value</strong> is what the model first read — it is not yet truth.
          </li>
          <li>
            <strong>Accepted</strong> is a reviewer&apos;s document-level decision — not yet an active assumption.
          </li>
          <li>
            <strong>Active fact</strong> is the promoted assumption; the <strong>draft</strong> and{' '}
            <strong>active baseline</strong> values may differ from it and from each other.
          </li>
          <li>
            <strong>Design-estimate</strong> values are not the same as weather-adjusted physics expectations.
          </li>
          <li>
            <strong>Legacy</strong> values (e.g. the former SiteAdditionalFieldList snapshot) are display-only — shown
            for comparison and never used to build a V2 baseline.
          </li>
        </Box>
      </Alert>

      <ReadinessSummary readiness={data.readiness} />

      {data.schema_expansion_recommended && (
        <Alert severity="info" sx={{ mb: 2 }} data-testid="reconciliation-schema-note">
          Some fields (for example GHI or P50/P90) carry more detail than the single-value point/row shape can fully
          represent. A schema expansion is recommended to capture them.
        </Alert>
      )}

      {!hasRows ? (
        <Paper variant="outlined" sx={{ p: 6, textAlign: 'center' }} data-testid="reconciliation-empty">
          <Typography variant="body1" color="text.secondary">
            No reconciliation rows are available for this project yet.
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Once diligence facts are extracted and reviewed, they will appear here.
          </Typography>
        </Paper>
      ) : (
        <>
          <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
              <TextField
                size="small"
                label="Filter fields"
                value={search}
                onChange={e => setSearch(e.target.value)}
                sx={{ minWidth: 200 }}
                inputProps={{ 'data-testid': 'reconciliation-search' }}
              />
              <TextField
                select
                size="small"
                label="Status"
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
                sx={{ minWidth: 180 }}
              >
                <MenuItem value="all">All statuses</MenuItem>
                {statusOptions.map(status => (
                  <MenuItem key={status} value={status}>
                    {statusMeta(status).label}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                size="small"
                label="Category"
                value={categoryFilter}
                onChange={e => setCategoryFilter(e.target.value)}
                sx={{ minWidth: 200 }}
              >
                <MenuItem value="all">All categories</MenuItem>
                {categoryOptions.map(category => (
                  <MenuItem key={category} value={category}>
                    {categoryLabel(category)}
                  </MenuItem>
                ))}
              </TextField>
              <FormControlLabel
                control={
                  <Switch
                    checked={warningsOnly}
                    onChange={e => setWarningsOnly(e.target.checked)}
                    data-testid="reconciliation-warnings-only"
                  />
                }
                label="Only rows with warnings"
              />
              <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
                Showing {filteredRows.length} of {data.rows.length} fields
              </Typography>
            </Box>
          </Paper>

          {filteredRows.length === 0 ? (
            <Paper variant="outlined" sx={{ p: 4, textAlign: 'center' }} data-testid="reconciliation-no-matches">
              <Typography variant="body2" color="text.secondary">
                No fields match the current filters.
              </Typography>
            </Paper>
          ) : (
            <ReconciliationTable
              rows={filteredRows}
              helpTargets={data.help_targets}
              siteId={siteId}
              canEdit={canEdit}
            />
          )}
        </>
      )}

      <Alert severity="info" sx={{ mt: 3 }} data-testid="reconciliation-telemetry-note">
        {data.telemetry_reality.note}
        {data.telemetry_reality.last_reading_at
          ? ` Last reading: ${formatDateTime(data.telemetry_reality.last_reading_at)}.`
          : ''}
      </Alert>
    </Box>
  );
};

export default Reconciliation;

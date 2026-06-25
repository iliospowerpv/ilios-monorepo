import React from 'react';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import { AgChartsReact } from 'ag-charts-react';
import type { AgCartesianAxisOptions, AgCartesianChartOptions, AgLineSeriesOptions } from 'ag-charts-community';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';

import { ApiClient } from '../../../../../../../api';
import type { ExpectedPreviewBucket } from '../../../../../../../types/telemetryV2';

dayjs.extend(utc);

/** Rolling window the overlay previews (matches the backend default). */
export const OVERLAY_WINDOW_HOURS = 24;
/** Bucket size — hourly, matching the standard expected/actual preview. */
export const OVERLAY_BUCKET_SIZE = '1h';

interface DraftPreviewOverlayProps {
  siteId: number;
  /** The selected draft baseline to preview (never the active one). */
  draftId: number;
  /** Lifecycle status of the previewed baseline; only `draft`/`approved` are previewable. */
  baselineStatus: string;
}

/** One overlay row: the same bucket for the active and the draft curve. */
export interface DraftOverlayRow {
  /** Local, human-readable bucket label (category-axis key). */
  period: string;
  /** Active (live) expected AC power for the bucket — `null` is an honest gap, never 0. */
  active: number | null;
  /** Draft (not-active) expected AC power for the bucket — `null` is an honest gap, never 0. */
  draft: number | null;
}

/**
 * Pull an honest expected value from a preview bucket. Only `ok` buckets carry a
 * real number; `missing_inputs` / `pre_pto` (and any non-finite value) become
 * `null` so the chart shows a gap rather than a fabricated 0.
 */
const expectedOf = (bucket: ExpectedPreviewBucket | undefined): number | null => {
  if (!bucket || bucket.status !== 'ok') return null;
  const v = bucket.expected_power_kw;
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
};

/**
 * Merge the active and draft preview buckets onto a shared, time-ordered axis.
 * Buckets are keyed by their (naive-UTC) `bucket_start` so the two curves line
 * up exactly; a bucket missing from one series stays `null` (an honest gap).
 */
export const buildOverlayRows = (
  activeBuckets: ExpectedPreviewBucket[] | undefined | null,
  draftBuckets: ExpectedPreviewBucket[] | undefined | null
): DraftOverlayRow[] => {
  const byStart = new Map<string, { active?: ExpectedPreviewBucket; draft?: ExpectedPreviewBucket }>();
  (activeBuckets ?? []).forEach(b => {
    const entry = byStart.get(b.bucket_start) ?? {};
    entry.active = b;
    byStart.set(b.bucket_start, entry);
  });
  (draftBuckets ?? []).forEach(b => {
    const entry = byStart.get(b.bucket_start) ?? {};
    entry.draft = b;
    byStart.set(b.bucket_start, entry);
  });
  return Array.from(byStart.entries())
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([start, entry]) => ({
      period: dayjs.utc(start).local().format('MMM D, h A'),
      active: expectedOf(entry.active),
      draft: expectedOf(entry.draft)
    }));
};

/**
 * Read-only draft-vs-active expected overlay (Phase 1).
 *
 * Shows the expected AC-power curve a `draft`/`approved` baseline WOULD produce
 * (dashed, "Draft — not active") alongside the site's current ACTIVE expected
 * curve (solid, "Current active") over the same window. It is review-only: it
 * never activates, never persists, and never affects live O&M output. Gaps are
 * honest — a draft with a blocking physics verdict or missing inputs shows NO
 * curve (never a fabricated 0). The draft would only take over at activation;
 * historical periods stay period-effective.
 */
export const DraftPreviewOverlay: React.FC<DraftPreviewOverlayProps> = ({ siteId, draftId, baselineStatus }) => {
  const previewable = baselineStatus === 'draft' || baselineStatus === 'approved';

  // Stable window per (site, draft) so the query key doesn't churn each render.
  const window = React.useMemo(() => {
    const end = dayjs();
    const start = end.subtract(OVERLAY_WINDOW_HOURS, 'hour');
    return { start: start.toISOString(), end: end.toISOString() };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteId, draftId]);

  const enabled = previewable && Number.isSafeInteger(siteId) && siteId > 0 && Number.isSafeInteger(draftId);

  const draftQuery = useQuery({
    queryKey: ['site', 'expected-baseline-draft-preview', { siteId, draftId, ...window }],
    queryFn: () =>
      ApiClient.telemetryV2.getDraftBaselinePreview(siteId, draftId, {
        start: window.start,
        end: window.end,
        bucketSize: OVERLAY_BUCKET_SIZE
      }),
    enabled,
    retry: false
  });

  // Active (live) curve over the same window — no baseline_id means "the active
  // baseline". `baseline_not_available` is returned (with no buckets) when none
  // is active; we surface that honestly rather than drawing a flat line.
  const activeQuery = useQuery({
    queryKey: ['site', 'expected-preview-active', { siteId, ...window }],
    queryFn: () =>
      ApiClient.telemetryV2.getExpectedPreview(siteId, {
        start: window.start,
        end: window.end,
        bucketSize: OVERLAY_BUCKET_SIZE
      }),
    enabled,
    retry: false
  });

  const rows = React.useMemo(
    () => buildOverlayRows(activeQuery.data?.buckets, draftQuery.data?.buckets),
    [activeQuery.data, draftQuery.data]
  );

  const series = React.useMemo<AgLineSeriesOptions[]>(
    () => [
      {
        type: 'line',
        xKey: 'period',
        yKey: 'active',
        yName: 'Current active',
        stroke: '#1976d2',
        strokeWidth: 2,
        connectMissingData: false,
        marker: { enabled: false }
      },
      {
        type: 'line',
        xKey: 'period',
        yKey: 'draft',
        yName: 'Draft (not active)',
        stroke: '#ed6c02',
        strokeWidth: 2,
        lineDash: [6, 4],
        connectMissingData: false,
        marker: { enabled: false }
      }
    ],
    []
  );

  const options = React.useMemo<AgCartesianChartOptions>(
    () => ({
      data: rows,
      series,
      height: 300,
      legend: { enabled: true, position: 'bottom' },
      axes: [
        {
          type: 'category',
          position: 'bottom',
          gridLine: { style: [{ stroke: 'lightgray' }] },
          line: { enabled: false },
          label: { fontFamily: 'Lato, sans-serif', rotation: -30 }
        },
        {
          type: 'number',
          position: 'left',
          keys: ['active', 'draft'],
          label: { fontFamily: 'Lato, sans-serif' },
          title: { text: 'Expected AC Power (kW)', fontFamily: 'Lato, sans-serif' },
          gridLine: { style: [{ stroke: 'lightgrey' }] }
        }
      ] as AgCartesianAxisOptions[]
    }),
    [rows, series]
  );

  if (!previewable) {
    return (
      <Alert severity="info" sx={{ mt: 1.5 }} data-testid="draft-preview-overlay-not-previewable">
        Expected preview is available for <strong>draft</strong> or <strong>approved</strong> baselines only. This
        baseline is &quot;{baselineStatus}&quot;.
      </Alert>
    );
  }

  const draftBlocked = draftQuery.data?.overall_status === 'baseline_invalid';
  const activeUnavailable = !activeQuery.isLoading && activeQuery.data?.overall_status !== 'ok';
  const isLoading = draftQuery.isLoading || activeQuery.isLoading;
  const isError = draftQuery.isError;

  return (
    <Box sx={{ mt: 1.5 }} data-testid="draft-preview-overlay">
      <Typography variant="overline" color="text.secondary">
        Draft vs. active expected preview (last {OVERLAY_WINDOW_HOURS}h)
      </Typography>

      <Alert severity="info" sx={{ mb: 1 }} data-testid="draft-preview-overlay-disclaimer">
        {draftQuery.data?.disclaimer ??
          'Preview of a draft/approved baseline that is NOT active. Numbers are for review only and do not affect any live expected-performance output.'}{' '}
        The draft would only take over <strong>at activation</strong>; historical periods stay period-effective.
      </Alert>

      {isLoading && (
        <Box display="flex" alignItems="center" gap={1} sx={{ my: 2 }} data-testid="draft-preview-overlay-loading">
          <CircularProgress size={16} />
          <Typography variant="body2" color="text.secondary">
            Loading draft-vs-active preview…
          </Typography>
        </Box>
      )}

      {!isLoading && isError && (
        <Alert severity="warning" sx={{ my: 1 }} data-testid="draft-preview-overlay-error">
          Couldn&apos;t load the draft preview right now. No expected curve is shown.
        </Alert>
      )}

      {!isLoading && !isError && draftBlocked && (
        <Alert severity="warning" sx={{ my: 1 }} data-testid="draft-preview-overlay-suppressed">
          <AlertTitle>Draft expected curve suppressed</AlertTitle>
          {(draftQuery.data?.validation_summary?.summary as string | undefined) ??
            'This draft fails fail-closed physics validation, so no expected curve is shown (never 0). Correct the source-backed inputs before activation.'}
        </Alert>
      )}

      {!isLoading && !isError && activeUnavailable && (
        <Typography
          variant="caption"
          color="text.secondary"
          display="block"
          sx={{ mb: 1 }}
          data-testid="draft-preview-overlay-no-active"
        >
          No active baseline is driving expected output yet — only the draft curve is shown for comparison.
        </Typography>
      )}

      {!isLoading && !isError && !draftBlocked && rows.length === 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ my: 1 }} data-testid="draft-preview-overlay-empty">
          No expected buckets in the last {OVERLAY_WINDOW_HOURS} hours for either curve.
        </Typography>
      )}

      {!isLoading && !isError && !draftBlocked && rows.length > 0 && (
        <Box data-testid="draft-preview-overlay-chart">
          <AgChartsReact options={options} />
        </Box>
      )}
    </Box>
  );
};

export default DraftPreviewOverlay;

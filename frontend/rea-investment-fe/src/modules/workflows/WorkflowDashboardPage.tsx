import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardActions from '@mui/material/CardActions';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import LinearProgress from '@mui/material/LinearProgress';
import Tooltip from '@mui/material/Tooltip';
import { ApiClient } from '../../api';
import { useNotify } from '../../contexts/notifications/notifications';
import type {
  WorkflowDefinitionSchema,
  WorkflowRunSummarySchema,
  SequenceSchema,
  RecommendationSchema,
  SiteOnboardingProgressSchema,
  SiteReadinessSchema,
  ReadinessSectionSchema
} from '../../api/workflows';
import { resolveLandingRoute, formatRunTimestamp, WORKFLOW_START_ROUTES, resolveSequenceRoute } from './landing';

/**
 * Native Workflow Dashboard. A discovery + resume surface over the existing engine: it reads the
 * owner-scoped run list, the registry definitions, and the declarative sequences, then groups them
 * into Suggested / In Progress / Available / Completed. It performs NO writes other than the
 * existing "abandon" (Cancel) call; every Start/Resume navigates to a page that drives the engine's
 * preview -> confirm -> execute handshake. The server remains the authoritative permission boundary.
 */

const SectionHeading: React.FC<{ title: string; caption?: string }> = ({ title, caption }) => (
  <Box sx={{ mb: 2, mt: 4 }}>
    <Typography variant="h6" fontWeight={600}>
      {title}
    </Typography>
    {caption && (
      <Typography variant="body2" color="text.secondary">
        {caption}
      </Typography>
    )}
  </Box>
);

const EmptyHint: React.FC<{ text: string }> = ({ text }) => (
  <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
    {text}
  </Typography>
);

const StatTile: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <Card variant="outlined" sx={{ height: '100%' }}>
    <CardContent>
      <Typography variant="h5" fontWeight={700}>
        {value}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
    </CardContent>
  </Card>
);

// Rates arrive as fractions in [0, 1]; durations as seconds. Both may be null (no closed runs yet).
const formatPercent = (value: number | null | undefined): string =>
  value == null ? '—' : `${Math.round(value * 100)}%`;

// Read-only next-action card. `route` is an internal path (it may carry a query string, e.g.
// `?site_id=`); a null route or a blocked rec disables the button. Clicking only navigates — the
// destination page still drives the engine's guarded preview -> confirm -> execute handshake.
const RecommendationCard: React.FC<{ rec: RecommendationSchema; onGo: (route: string) => void }> = ({
  rec,
  onGo
}) => (
  <Card variant="outlined" sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
    <CardContent sx={{ flexGrow: 1 }}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="subtitle1" fontWeight={600}>
          {rec.title}
        </Typography>
        <Chip label={rec.kind === 'sequence' ? 'Setup' : 'Action'} size="small" color="primary" variant="outlined" />
      </Stack>
      <Typography variant="body2" color="text.secondary">
        {rec.reason}
      </Typography>
      {rec.blocked && rec.blocked_reason && (
        <Typography variant="caption" color="warning.main" sx={{ display: 'block', mt: 1 }}>
          {rec.blocked_reason}
        </Typography>
      )}
    </CardContent>
    <CardActions sx={{ px: 2, pb: 2 }}>
      <Button
        variant="contained"
        size="small"
        disabled={rec.blocked || !rec.route}
        onClick={() => rec.route && onGo(rec.route)}
      >
        Go
      </Button>
    </CardActions>
  </Card>
);

// One onboarding-stage chip. A stage the caller can't evaluate (`available=false`) is rendered as a
// neutral, disabled "locked" chip — never silently counted as done.
const StageChip: React.FC<{ label: string; done: boolean; available: boolean; detail?: string | null }> = ({
  label,
  done,
  available,
  detail
}) => {
  const chip = (
    <Chip
      label={label}
      size="small"
      variant={done ? 'filled' : 'outlined'}
      color={!available ? 'default' : done ? 'success' : 'warning'}
      disabled={!available}
    />
  );
  return detail ? <Tooltip title={detail}>{chip}</Tooltip> : chip;
};

// Map a readiness section's verdict to a chip color. Honest "unavailable" semantics: a denied or
// unreadable section is a neutral chip, NEVER a failing/zero state.
const readinessChipColor = (section: ReadinessSectionSchema): 'default' | 'success' | 'warning' | 'error' => {
  if (!section.available) return 'default';
  const status = (section.status ?? '').toLowerCase();
  if (['ready', 'healthy', 'ok', 'good', 'complete', 'active'].includes(status)) return 'success';
  if (['error', 'failed', 'critical', 'invalid'].includes(status)) return 'error';
  return 'warning';
};

const ReadinessChip: React.FC<{ label: string; section: ReadinessSectionSchema }> = ({ label, section }) => {
  const text = !section.available ? 'Unavailable' : section.status ?? section.summary ?? '—';
  const tip = !section.available
    ? section.reason === 'permission_denied'
      ? "You don't have access to this dimension."
      : section.reason ?? 'This dimension could not be read.'
    : section.summary ?? undefined;
  const chip = (
    <Chip label={`${label}: ${text}`} size="small" variant="outlined" color={readinessChipColor(section)} />
  );
  return tip ? <Tooltip title={tip}>{chip}</Tooltip> : chip;
};

const formatDuration = (seconds: number | null | undefined): string => {
  if (seconds == null) return '—';
  const total = Math.round(seconds);
  if (total < 60) return `${total}s`;
  const minutes = Math.floor(total / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const remMin = minutes % 60;
  return remMin ? `${hours}h ${remMin}m` : `${hours}h`;
};

const WorkflowDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const notify = useNotify();
  const queryClient = useQueryClient();

  const definitionsQuery = useQuery({
    queryKey: ['workflows', 'definitions'],
    queryFn: () => ApiClient.workflows.list()
  });
  const runsQuery = useQuery({
    queryKey: ['workflows', 'runs'],
    queryFn: () => ApiClient.workflows.listRuns({ limit: 100 })
  });
  const sequencesQuery = useQuery({
    queryKey: ['workflows', 'sequences'],
    queryFn: () => ApiClient.workflows.listSequences()
  });
  // Read-only, owner-scoped completion metrics. Failure is non-blocking — the dashboard still works.
  const metricsQuery = useQuery({
    queryKey: ['workflows', 'metrics', 'me'],
    queryFn: () => ApiClient.workflows.getMetrics('me')
  });
  // Phase 3 read-only aggregations. Each is independently non-blocking: a failure hides its own
  // panel but never breaks the rest of the dashboard.
  const recommendationsQuery = useQuery({
    queryKey: ['workflows', 'recommendations'],
    queryFn: () => ApiClient.workflows.getRecommendations()
  });
  const progressQuery = useQuery({
    queryKey: ['workflows', 'onboarding', 'progress'],
    queryFn: () => ApiClient.workflows.getOnboardingProgress({ limit: 25 })
  });
  const readinessQuery = useQuery({
    queryKey: ['workflows', 'onboarding', 'readiness'],
    queryFn: () => ApiClient.workflows.getReadiness({ limit: 25 })
  });

  const cancelMutation = useMutation({
    mutationFn: (runId: number) => ApiClient.workflows.abandon(runId),
    onSuccess: () => {
      notify('Workflow cancelled.');
      queryClient.invalidateQueries({ queryKey: ['workflows', 'runs'] });
    },
    onError: () => notify('Could not cancel this workflow.')
  });

  const isLoading = definitionsQuery.isLoading || runsQuery.isLoading || sequencesQuery.isLoading;
  const isError = definitionsQuery.isError || runsQuery.isError || sequencesQuery.isError;

  const runs: WorkflowRunSummarySchema[] = runsQuery.data?.items ?? [];
  const definitions: WorkflowDefinitionSchema[] = definitionsQuery.data?.items ?? [];
  const sequences: SequenceSchema[] = sequencesQuery.data?.items ?? [];

  const inProgress = runs.filter(r => r.status === 'active' || r.status === 'paused');
  const completed = runs.filter(r => r.status === 'completed');
  const metrics = metricsQuery.data;
  const recommendations: RecommendationSchema[] = recommendationsQuery.data?.items ?? [];
  const progressItems: SiteOnboardingProgressSchema[] = progressQuery.data?.items ?? [];
  const readinessItems: SiteReadinessSchema[] = readinessQuery.data?.items ?? [];

  const startSequence = (seq: SequenceSchema) => {
    navigate(resolveSequenceRoute(seq.id));
  };

  const startWorkflow = (def: WorkflowDefinitionSchema) => {
    const route = WORKFLOW_START_ROUTES[def.id];
    if (route) navigate(route);
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 4, maxWidth: 1080, mx: 'auto' }}>
      <Typography variant="h4" fontWeight={600} sx={{ mb: 1 }}>
        Workflows
      </Typography>
      <Typography variant="body1" color="text.secondary">
        Guided actions for setting up and managing your portfolio. Pick up where you left off, or start something new.
      </Typography>

      {isError && (
        <Alert severity="error" sx={{ mt: 3 }}>
          Some workflow data could not be loaded. Please refresh to try again.
        </Alert>
      )}

      {/* Recommended next — deterministic, READ-ONLY next-action hints. Each card only navigates;
          nothing is auto-started, promoted, approved, mapped, or declared. */}
      {recommendations.length > 0 && (
        <>
          <SectionHeading
            title="Recommended next"
            caption="Read-only suggestions for what to do next. Nothing happens until you start it."
          />
          <Grid container spacing={2}>
            {recommendations.map((rec, idx) => (
              <Grid item xs={12} md={6} key={`${rec.kind}-${rec.workflow_id ?? rec.sequence_id ?? idx}-${idx}`}>
                <RecommendationCard rec={rec} onGo={route => navigate(route)} />
              </Grid>
            ))}
          </Grid>
        </>
      )}

      {/* Your activity — read-only completion metrics over the caller's own runs. */}
      {metrics && metrics.total_runs > 0 && (
        <>
          <SectionHeading title="Your activity" caption="A read-only summary of the workflows you've run." />
          <Grid container spacing={2}>
            <Grid item xs={6} md={3}>
              <StatTile label="Total runs" value={String(metrics.total_runs)} />
            </Grid>
            <Grid item xs={6} md={3}>
              <StatTile label="Completed" value={String(metrics.completed_runs)} />
            </Grid>
            <Grid item xs={6} md={3}>
              <StatTile label="In progress" value={String(metrics.in_progress_runs)} />
            </Grid>
            <Grid item xs={6} md={3}>
              <StatTile label="Completion rate" value={formatPercent(metrics.completion_rate)} />
            </Grid>
            <Grid item xs={6} md={3}>
              <StatTile label="Abandonment rate" value={formatPercent(metrics.abandonment_rate)} />
            </Grid>
            <Grid item xs={6} md={3}>
              <StatTile label="Avg duration" value={formatDuration(metrics.avg_duration_seconds)} />
            </Grid>
            <Grid item xs={6} md={3}>
              <StatTile label="Median duration" value={formatDuration(metrics.median_duration_seconds)} />
            </Grid>
          </Grid>
        </>
      )}

      {/* Suggested — declarative multi-step sequences (e.g. onboarding). */}
      {sequences.length > 0 && (
        <>
          <SectionHeading title="Suggested" caption="Recommended multi-step setups." />
          <Grid container spacing={2}>
            {sequences.map(seq => (
              <Grid item xs={12} md={6} key={seq.id}>
                <Card variant="outlined" sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        {seq.title}
                      </Typography>
                      <Chip label={seq.category} size="small" />
                    </Stack>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                      {seq.description}
                    </Typography>
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                      {seq.steps.map((step, idx) => (
                        <Chip
                          key={step.workflow_id}
                          label={`${idx + 1}. ${step.title}`}
                          size="small"
                          variant="outlined"
                          color={step.can_start ? 'default' : 'warning'}
                        />
                      ))}
                    </Stack>
                  </CardContent>
                  <CardActions sx={{ px: 2, pb: 2 }}>
                    <Button variant="contained" disabled={!seq.can_start} onClick={() => startSequence(seq)}>
                      Start
                    </Button>
                    {!seq.can_start && (
                      <Typography variant="caption" color="text.secondary">
                        You don&apos;t have permission to start the first step.
                      </Typography>
                    )}
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        </>
      )}

      {/* Onboarding progress — per-project stage checklist, derived only from existing service
          verdicts. Stages the caller can't evaluate render locked, never counted as done. */}
      {progressItems.length > 0 && (
        <>
          <SectionHeading
            title="Onboarding progress"
            caption="How far each project has come through setup. Read-only — based on your current data."
          />
          <Grid container spacing={2}>
            {progressItems.map(item => (
              <Grid item xs={12} md={6} key={item.site_id}>
                <Card variant="outlined" sx={{ height: '100%' }}>
                  <CardContent>
                    <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        {item.site_name ?? `Project ${item.site_id}`}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {item.completed_stages}/{item.total_stages}
                      </Typography>
                    </Stack>
                    <LinearProgress
                      variant="determinate"
                      value={Math.round((item.completion_rate ?? 0) * 100)}
                      sx={{ mb: 1.5, height: 8, borderRadius: 1 }}
                    />
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                      {item.stages.map(stage => (
                        <StageChip
                          key={stage.key}
                          label={stage.label}
                          done={stage.done}
                          available={stage.available}
                          detail={stage.detail}
                        />
                      ))}
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </>
      )}

      {/* Readiness — per-project summary across telemetry health, reconciliation, device eligibility
          and expected-baseline existence. A denied/unreadable dimension degrades to a neutral
          "Unavailable" chip — never a failing/zero state. */}
      {readinessItems.length > 0 && (
        <>
          <SectionHeading
            title="Readiness"
            caption="A read-only health snapshot per project. Dimensions you can't access show as unavailable."
          />
          <Grid container spacing={2}>
            {readinessItems.map(item => (
              <Grid item xs={12} md={6} key={item.site_id}>
                <Card variant="outlined" sx={{ height: '100%' }}>
                  <CardContent>
                    <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1.5 }}>
                      {item.site_name ?? `Project ${item.site_id}`}
                    </Typography>
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                      <ReadinessChip label="Telemetry" section={item.telemetry_health} />
                      <ReadinessChip label="Reconciliation" section={item.reconciliation} />
                      <ReadinessChip label="Devices" section={item.device_eligibility} />
                      <ReadinessChip label="Baseline" section={item.expected_baseline} />
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </>
      )}

      {/* In Progress — resumable / cancellable owner-scoped runs. */}
      <SectionHeading title="In Progress" caption="Workflows you've started but not finished." />
      {inProgress.length === 0 ? (
        <EmptyHint text="Nothing in progress." />
      ) : (
        <Grid container spacing={2}>
          {inProgress.map(run => (
            <Grid item xs={12} md={6} key={run.id}>
              <Card variant="outlined" sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <CardContent sx={{ flexGrow: 1 }}>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                    <Typography variant="subtitle1" fontWeight={600}>
                      {run.workflow_title ?? run.workflow_id}
                    </Typography>
                    <Chip label={run.status} size="small" color="info" />
                    {run.sequence_id && <Chip label="Onboarding" size="small" variant="outlined" />}
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    Started {formatRunTimestamp(run.created_at)}
                  </Typography>
                </CardContent>
                <CardActions sx={{ px: 2, pb: 2 }}>
                  <Button variant="contained" onClick={() => navigate(`/workflows/run/${run.id}`)}>
                    Resume
                  </Button>
                  <Button
                    color="error"
                    disabled={cancelMutation.isPending}
                    onClick={() => cancelMutation.mutate(run.id)}
                  >
                    Cancel
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Available — single workflows the user can start now. */}
      <SectionHeading title="Available" caption="Single actions you can start now." />
      {definitions.length === 0 ? (
        <EmptyHint text="No workflows are available to you." />
      ) : (
        <Grid container spacing={2}>
          {definitions.map(def => (
            <Grid item xs={12} md={6} key={def.id}>
              <Card variant="outlined" sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <CardContent sx={{ flexGrow: 1 }}>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                    <Typography variant="subtitle1" fontWeight={600}>
                      {def.title}
                    </Typography>
                    <Chip label={def.category} size="small" />
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    {def.description}
                  </Typography>
                </CardContent>
                <CardActions sx={{ px: 2, pb: 2, flexDirection: 'column', alignItems: 'flex-start', gap: 1 }}>
                  <Button
                    variant="outlined"
                    disabled={!WORKFLOW_START_ROUTES[def.id] || !!def.blocked_reason}
                    onClick={() => startWorkflow(def)}
                  >
                    Start
                  </Button>
                  {def.blocked_reason && (
                    <Typography variant="caption" color="text.secondary">
                      {def.blocked_reason}
                    </Typography>
                  )}
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Completed — recent finished runs with a link to the created entity. */}
      <SectionHeading title="Completed" caption="Recently finished workflows." />
      {completed.length === 0 ? (
        <EmptyHint text="Nothing completed yet." />
      ) : (
        <Grid container spacing={2}>
          {completed.map(run => {
            const landing = resolveLandingRoute(run.landing_route_template, run.result_entity_id);
            return (
              <Grid item xs={12} md={6} key={run.id}>
                <Card variant="outlined" sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        {run.workflow_title ?? run.workflow_id}
                      </Typography>
                      <Chip label="Completed" size="small" color="success" />
                    </Stack>
                    <Typography variant="body2" color="text.secondary">
                      Finished {formatRunTimestamp(run.updated_at)}
                    </Typography>
                  </CardContent>
                  <CardActions sx={{ px: 2, pb: 2 }}>
                    <Button variant="text" disabled={!landing} onClick={() => landing && navigate(landing)}>
                      View result
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}
    </Box>
  );
};

export default WorkflowDashboardPage;

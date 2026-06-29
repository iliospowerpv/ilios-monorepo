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
import { ApiClient } from '../../api';
import { useNotify } from '../../contexts/notifications/notifications';
import type { WorkflowDefinitionSchema, WorkflowRunSummarySchema, SequenceSchema } from '../../api/workflows';
import { resolveLandingRoute, formatRunTimestamp, WORKFLOW_START_ROUTES, SEQUENCE_START_ROUTES } from './landing';

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

  const startSequence = (seq: SequenceSchema) => {
    const route = SEQUENCE_START_ROUTES[seq.id];
    if (route) navigate(route);
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
                    <Button
                      variant="contained"
                      disabled={!seq.can_start || !SEQUENCE_START_ROUTES[seq.id]}
                      onClick={() => startSequence(seq)}
                    >
                      Start onboarding
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

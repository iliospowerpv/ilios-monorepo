import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { useNavigate, useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import CircularProgress from '@mui/material/CircularProgress';
import { ApiClient } from '../../api';
import { useNotify } from '../../contexts/notifications/notifications';
import { Wizard } from '../../components/common/Wizard';
import type {
  WorkflowRunDetailResponse,
  ExecuteResponse,
  PreviewResponse,
  WorkflowStepStateSchema
} from '../../api/workflows';
import { resolveLandingRoute } from './landing';

/**
 * Generic resume page for the native Workflow Engine. Loads an EXISTING run by id and hands its
 * saved definition + run state to the reusable <Wizard>, which resumes from `current_step` and
 * re-seeds previously collected inputs. Used by the Workflow Dashboard's "Resume" action. The page
 * only wires the API + landing redirect; the server still owns orchestration and every write.
 */
const WorkflowRunPage: React.FC = () => {
  const navigate = useNavigate();
  const notify = useNotify();
  const { runId: runIdParam } = useParams<{ runId: string }>();
  const runId = runIdParam ? parseInt(runIdParam, 10) : NaN;
  const [detail, setDetail] = useState<WorkflowRunDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const loadedRef = useRef(false);

  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;
    if (Number.isNaN(runId)) {
      setError('That workflow could not be found.');
      setLoading(false);
      return;
    }
    (async () => {
      try {
        const result = await ApiClient.workflows.getRun(runId);
        if (result.run.status !== 'active') {
          setError('This workflow is no longer in progress.');
        } else {
          setDetail(result);
        }
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 404) {
          setError('That workflow could not be found.');
        } else {
          setError('Could not load this workflow. Please try again.');
        }
      } finally {
        setLoading(false);
      }
    })();
  }, [runId]);

  const handleSaveStep = (stepId: string, inputs: Record<string, unknown>): Promise<WorkflowStepStateSchema> =>
    ApiClient.workflows.saveStep(detail!.run.id, stepId, inputs);

  const handlePreview = (stepId: string): Promise<PreviewResponse> => ApiClient.workflows.preview(detail!.run.id, stepId);

  const handleExecute = (stepId: string, confirmToken: string, idempotencyKey: string): Promise<ExecuteResponse> =>
    ApiClient.workflows.execute(detail!.run.id, stepId, {
      confirm_token: confirmToken,
      idempotency_key: idempotencyKey
    });

  const handleComplete = (result: ExecuteResponse) => {
    notify(result.message || 'Completed successfully.');
    const landing = resolveLandingRoute(detail?.definition.landing_route_template, result.entity_id);
    navigate(landing ?? '/workflows');
  };

  const handleExit = async () => {
    if (detail) {
      try {
        await ApiClient.workflows.abandon(detail.run.id);
      } catch {
        // Best-effort: abandoning is a courtesy cleanup, never a blocker.
      }
    }
    navigate('/workflows');
  };

  return (
    <Box sx={{ p: 4, maxWidth: 760, mx: 'auto' }}>
      <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 3 }}>
        <IconButton onClick={() => navigate('/workflows')} size="small">
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4" fontWeight={600}>
          {detail?.definition.title ?? 'Resume workflow'}
        </Typography>
      </Stack>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      )}

      {!loading && error && (
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={() => navigate('/workflows')}>
              Back to workflows
            </Button>
          }
        >
          {error}
        </Alert>
      )}

      {!loading && !error && detail && (
        <Wizard
          definition={detail.definition}
          run={detail.run}
          onSaveStep={handleSaveStep}
          onPreview={handlePreview}
          onExecute={handleExecute}
          onComplete={handleComplete}
          onExit={handleExit}
          notify={notify}
        />
      )}
    </Box>
  );
};

export default WorkflowRunPage;

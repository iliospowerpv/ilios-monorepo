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
 * Generic start page for the native Workflow Engine, keyed off the route `:workflowId`. It starts a
 * fresh run for ANY registered single workflow and hands the serialized definition + run to the
 * reusable <Wizard>. Unlike the bespoke add_company / add_site pages, it also wires:
 *   - onExecuteFile: multipart execute for steps declaring `multipart_file_field` (document upload), and
 *   - onReloadRun: re-fetch the run after each save so context-dependent options refresh
 *     (e.g. project -> documents -> files).
 * The server still owns orchestration, permissions, and every write; this page only wires the API
 * and the post-completion landing redirect.
 */
const GenericWorkflowStartPage: React.FC = () => {
  const navigate = useNavigate();
  const notify = useNotify();
  const { workflowId } = useParams<{ workflowId: string }>();
  const [detail, setDetail] = useState<WorkflowRunDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    if (!workflowId) {
      setError('That workflow could not be found.');
      setLoading(false);
      return;
    }
    (async () => {
      try {
        const result = await ApiClient.workflows.startRun(workflowId);
        setDetail(result);
      } catch (err) {
        if (axios.isAxiosError(err)) {
          const status = err.response?.status;
          if (status === 403) {
            setError("You don't have permission to start this workflow.");
          } else if (status === 404) {
            setError('That workflow could not be found.');
          } else {
            setError('Could not start this workflow. Please try again.');
          }
        } else {
          setError('Could not start this workflow. Please try again.');
        }
      } finally {
        setLoading(false);
      }
    })();
  }, [workflowId]);

  const handleSaveStep = (stepId: string, inputs: Record<string, unknown>): Promise<WorkflowStepStateSchema> =>
    ApiClient.workflows.saveStep(detail!.run.id, stepId, inputs);

  const handlePreview = (stepId: string): Promise<PreviewResponse> =>
    ApiClient.workflows.preview(detail!.run.id, stepId);

  const handleExecute = (stepId: string, confirmToken: string, idempotencyKey: string): Promise<ExecuteResponse> =>
    ApiClient.workflows.execute(detail!.run.id, stepId, {
      confirm_token: confirmToken,
      idempotency_key: idempotencyKey
    });

  const handleExecuteFile = (
    stepId: string,
    confirmToken: string,
    idempotencyKey: string,
    file: File
  ): Promise<ExecuteResponse> =>
    ApiClient.workflows.executeFile(
      detail!.run.id,
      stepId,
      { confirm_token: confirmToken, idempotency_key: idempotencyKey },
      file
    );

  // Re-fetch the run so the wizard can refresh context-dependent (cascading) options after a save.
  const handleReloadRun = (): Promise<WorkflowRunDetailResponse> => ApiClient.workflows.getRun(detail!.run.id);

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
          {detail?.definition.title ?? 'Start workflow'}
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
          onExecuteFile={handleExecuteFile}
          onReloadRun={handleReloadRun}
          onComplete={handleComplete}
          onExit={handleExit}
          notify={notify}
        />
      )}
    </Box>
  );
};

export default GenericWorkflowStartPage;

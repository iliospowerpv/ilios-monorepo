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
import Stepper from '@mui/material/Stepper';
import Step from '@mui/material/Step';
import StepLabel from '@mui/material/StepLabel';
import { ApiClient } from '../../api';
import { useNotify } from '../../contexts/notifications/notifications';
import { Wizard } from '../../components/common/Wizard';
import type {
  SequenceSchema,
  WorkflowRunDetailResponse,
  WorkflowRunSchema,
  WorkflowStepStateSchema,
  StartRunRequest,
  ExecuteResponse,
  PreviewResponse
} from '../../api/workflows';
import { resolveLandingRoute } from './landing';

/**
 * Generic Sequence Runner for the native Workflow Engine. Walks ANY declarative SequenceDef
 * (`/workflows/sequences/:sequenceId`) by chaining its otherwise-INDEPENDENT step workflows into one
 * guided journey. For each step it:
 *   - starts a fresh run with orchestration lineage (sequence_id + step index + parent_run_id) so the
 *     server can audit the chain,
 *   - applies the sequence's DECLARATIVE prefill hints — copying an entity id created by an earlier
 *     step into this step's collect field WITHOUT any server write (a client-only seed of the run's
 *     collected inputs),
 *   - hands the serialized definition + run to the reusable <Wizard>, which still drives the engine's
 *     preview -> confirm -> execute handshake.
 * The runner itself never mutates operational truth; every write goes through the engine's guarded
 * execute pipeline, and the server remains the authoritative permission boundary.
 */

const permissionOrGeneric = (err: unknown, action: string): string => {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status;
    if (status === 403) return `You don't have permission to ${action}.`;
    if (status === 404) return 'That step could not be found.';
  }
  return 'Could not start this step. Please try again.';
};

const SequenceRunnerPage: React.FC = () => {
  const navigate = useNavigate();
  const notify = useNotify();
  const { sequenceId } = useParams<{ sequenceId: string }>();

  const [sequence, setSequence] = useState<SequenceSchema | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [detail, setDetail] = useState<WorkflowRunDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Entity ids produced by each completed step, keyed by step index — the source for prefill hints.
  const producedRef = useRef<Record<number, number>>({});
  const startedRef = useRef(false);

  // Start the run for `index`, seeding declarative prefill from already-produced entities. `parent`
  // chains lineage to the immediately prior step's run (null for the first step).
  const startStep = async (seq: SequenceSchema, index: number, parent: number | null) => {
    setLoading(true);
    setError(null);
    const step = seq.steps[index];
    const body: StartRunRequest = {
      sequence_id: seq.id,
      sequence_step_index: index,
      parent_run_id: parent
    };
    // Build the client-only seed for this step's first collect field(s) from earlier results.
    const seed: Record<string, unknown> = {};
    for (const hint of step.prefill ?? []) {
      const entityId = producedRef.current[hint.from_step_index];
      if (entityId == null) continue;
      seed[hint.target_field] = String(entityId);
      // company_id / site_id also scope the run server-side (the engine validates ownership).
      if (hint.target_field === 'company_id') body.company_id = entityId;
      if (hint.target_field === 'site_id') body.site_id = entityId;
    }
    try {
      const result = await ApiClient.workflows.startRun(step.workflow_id, body);
      // Seed the first collect step's inputs WITHOUT a server write (mirrors the run's collected
      // inputs client-side); the underlying workflow still validates + authorizes them at execute.
      const collectStepId = result.definition.steps[0]?.id;
      const seededRun: WorkflowRunSchema =
        collectStepId && Object.keys(seed).length > 0
          ? {
              ...result.run,
              step_states: [
                {
                  step_id: collectStepId,
                  inputs: seed,
                  validation_status: 'pending',
                  executed: false
                } as WorkflowStepStateSchema
              ]
            }
          : result.run;
      setDetail({ ...result, run: seededRun });
      setStepIndex(index);
    } catch (err) {
      setError(permissionOrGeneric(err, `start "${step.title}"`));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    if (!sequenceId) {
      setError('That sequence could not be found.');
      setLoading(false);
      return;
    }
    (async () => {
      try {
        const list = await ApiClient.workflows.listSequences();
        const seq = list.items.find(s => s.id === sequenceId) ?? null;
        if (!seq) {
          setError('That sequence could not be found.');
          setLoading(false);
          return;
        }
        if (seq.steps.length === 0) {
          setError('This sequence has no steps to run.');
          setLoading(false);
          return;
        }
        setSequence(seq);
        await startStep(seq, 0, null);
      } catch (err) {
        setError(permissionOrGeneric(err, 'start this sequence'));
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sequenceId]);

  const handleSaveStep = (stepId: string, inputs: Record<string, unknown>): Promise<WorkflowStepStateSchema> =>
    ApiClient.workflows.saveStep(detail!.run.id, stepId, inputs);

  const handlePreview = (stepId: string): Promise<PreviewResponse> => ApiClient.workflows.preview(detail!.run.id, stepId);

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
    notify(result.message || 'Step completed.');
    if (!sequence) {
      navigate('/workflows');
      return;
    }
    // Record this step's produced entity so later steps can prefill from it.
    if (result.entity_id != null) {
      producedRef.current[stepIndex] = result.entity_id;
    }
    const next = stepIndex + 1;
    if (next < sequence.steps.length) {
      const parentRunId = detail?.run.id ?? null;
      startStep(sequence, next, parentRunId);
    } else {
      // Last step — land on the produced entity when the workflow advertises a landing template.
      const landing = resolveLandingRoute(detail?.definition.landing_route_template, result.entity_id);
      navigate(landing ?? '/workflows');
    }
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
          {sequence?.title ?? 'Guided setup'}
        </Typography>
      </Stack>

      {sequence && sequence.steps.length > 1 && (
        <Stepper activeStep={stepIndex} alternativeLabel sx={{ mb: 4 }}>
          {sequence.steps.map((step, idx) => (
            <Step key={`${step.workflow_id}-${idx}`}>
              <StepLabel>{step.title}</StepLabel>
            </Step>
          ))}
        </Stepper>
      )}

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
          key={detail.run.id}
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

export default SequenceRunnerPage;

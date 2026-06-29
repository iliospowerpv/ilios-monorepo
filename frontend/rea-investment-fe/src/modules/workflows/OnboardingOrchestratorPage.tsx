import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
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
  WorkflowRunDetailResponse,
  WorkflowRunSchema,
  ExecuteResponse,
  PreviewResponse,
  WorkflowStepStateSchema
} from '../../api/workflows';
import { resolveLandingRoute } from './landing';

/**
 * Native Onboarding Orchestrator. Chains two INDEPENDENT engine workflows — Add Company then
 * Add Project (= Site) — into one guided flow. It starts each step's run with orchestration
 * lineage (sequence_id + step index + parent_run_id) so the server can audit the chain, captures
 * the created company id from the first step's execute response, and prefills it into the second
 * step's company picker WITHOUT any server write (the prefill is a client-only seed of the run's
 * collected inputs). Each underlying run still goes through the engine's preview -> confirm ->
 * execute handshake; the orchestrator itself never mutates operational truth.
 */

const ONBOARDING_SEQUENCE_ID = 'onboarding';
const STEP_LABELS = ['Add Company', 'Add Project'];

const permissionOrGeneric = (err: unknown, action: string): string => {
  if (axios.isAxiosError(err) && err.response?.status === 403) {
    return `You don't have permission to ${action}.`;
  }
  return 'Could not start this step. Please try again.';
};

const OnboardingOrchestratorPage: React.FC = () => {
  const navigate = useNavigate();
  const notify = useNotify();
  const [phase, setPhase] = useState<'company' | 'site'>('company');
  const [detail, setDetail] = useState<WorkflowRunDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    (async () => {
      try {
        const result = await ApiClient.workflows.startRun('add_company', {
          sequence_id: ONBOARDING_SEQUENCE_ID,
          sequence_step_index: 0
        });
        setDetail(result);
      } catch (err) {
        setError(permissionOrGeneric(err, 'add a company'));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const startSite = async (companyId: number, parentRunId: number) => {
    setLoading(true);
    setError(null);
    try {
      const result = await ApiClient.workflows.startRun('add_site', {
        sequence_id: ONBOARDING_SEQUENCE_ID,
        sequence_step_index: 1,
        parent_run_id: parentRunId,
        company_id: companyId
      });
      // Prefill the company picker with NO server write: seed the collect step's inputs client-side.
      const collectStepId = result.definition.steps[0]?.id;
      const seededRun: WorkflowRunSchema = collectStepId
        ? {
            ...result.run,
            step_states: [
              {
                step_id: collectStepId,
                inputs: { company_id: String(companyId) },
                validation_status: 'pending',
                executed: false
              } as WorkflowStepStateSchema
            ]
          }
        : result.run;
      setDetail({ ...result, run: seededRun });
      setPhase('site');
    } catch (err) {
      setError(permissionOrGeneric(err, 'add a project'));
    } finally {
      setLoading(false);
    }
  };

  const handleSaveStep = (stepId: string, inputs: Record<string, unknown>): Promise<WorkflowStepStateSchema> =>
    ApiClient.workflows.saveStep(detail!.run.id, stepId, inputs);

  const handlePreview = (stepId: string): Promise<PreviewResponse> => ApiClient.workflows.preview(detail!.run.id, stepId);

  const handleExecute = (stepId: string, confirmToken: string, idempotencyKey: string): Promise<ExecuteResponse> =>
    ApiClient.workflows.execute(detail!.run.id, stepId, {
      confirm_token: confirmToken,
      idempotency_key: idempotencyKey
    });

  const handleComplete = (result: ExecuteResponse) => {
    if (phase === 'company') {
      notify(result.message || 'Company created.');
      const companyId = result.entity_id ?? null;
      const parentRunId = detail?.run.id ?? null;
      if (companyId && parentRunId) {
        startSite(companyId, parentRunId);
      } else {
        // Without the produced company id we can't safely chain — fall back to the dashboard.
        navigate('/workflows');
      }
    } else {
      notify(result.message || 'Project created.');
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

  const activeStep = phase === 'company' ? 0 : 1;

  return (
    <Box sx={{ p: 4, maxWidth: 760, mx: 'auto' }}>
      <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 3 }}>
        <IconButton onClick={() => navigate('/workflows')} size="small">
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4" fontWeight={600}>
          Onboarding
        </Typography>
      </Stack>

      <Stepper activeStep={activeStep} alternativeLabel sx={{ mb: 4 }}>
        {STEP_LABELS.map(label => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

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
          onComplete={handleComplete}
          onExit={handleExit}
          confirmLabel={phase === 'company' ? 'Create company' : 'Create project'}
          notify={notify}
        />
      )}
    </Box>
  );
};

export default OnboardingOrchestratorPage;

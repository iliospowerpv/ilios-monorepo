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
import { ApiClient } from '../../api';
import { useNotify } from '../../contexts/notifications/notifications';
import { Wizard } from '../../components/common/Wizard';
import type {
  WorkflowRunDetailResponse,
  ExecuteResponse,
  PreviewResponse,
  WorkflowStepStateSchema
} from '../../api/workflows';

/**
 * Pilot page for the native Workflow Engine. It starts an `add_company` run, then hands the
 * serialized definition + run to the reusable <Wizard> shell. The page owns only the API
 * wiring; the engine (server-side) owns orchestration and dispatches the write to the
 * EXISTING company-create endpoint behind a preview -> confirm -> execute handshake.
 */
const AddCompanyWorkflowPage: React.FC = () => {
  const navigate = useNavigate();
  const notify = useNotify();
  const [detail, setDetail] = useState<WorkflowRunDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    (async () => {
      try {
        const result = await ApiClient.workflows.startRun('add_company');
        setDetail(result);
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 403) {
          setError("You don't have permission to add a company.");
        } else {
          setError('Could not start this workflow. Please try again.');
        }
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleSaveStep = (stepId: string, inputs: Record<string, unknown>): Promise<WorkflowStepStateSchema> =>
    ApiClient.workflows.saveStep(detail!.run.id, stepId, inputs);

  const handlePreview = (stepId: string): Promise<PreviewResponse> =>
    ApiClient.workflows.preview(detail!.run.id, stepId);

  const handleExecute = (stepId: string, confirmToken: string, idempotencyKey: string): Promise<ExecuteResponse> =>
    ApiClient.workflows.execute(detail!.run.id, stepId, {
      confirm_token: confirmToken,
      idempotency_key: idempotencyKey
    });

  const handleComplete = (result: ExecuteResponse) => {
    notify(result.message || 'Company created successfully.');
    if (result.entity_id) {
      navigate(`/project-hub/companies/${result.entity_id}`);
    } else {
      navigate('/home');
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
    navigate('/home');
  };

  return (
    <Box sx={{ p: 4, maxWidth: 760, mx: 'auto' }}>
      <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 3 }}>
        <IconButton onClick={() => navigate(-1)} size="small">
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4" fontWeight={600}>
          Add Company
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
            <Button color="inherit" size="small" onClick={() => navigate('/home')}>
              Go home
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
          confirmLabel="Create company"
          notify={notify}
        />
      )}
    </Box>
  );
};

export default AddCompanyWorkflowPage;

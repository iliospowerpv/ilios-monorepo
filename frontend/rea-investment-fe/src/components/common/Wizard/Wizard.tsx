import React, { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Stepper from '@mui/material/Stepper';
import Step from '@mui/material/Step';
import StepLabel from '@mui/material/StepLabel';
import { ConfirmationModal } from '../../modals/ConfirmationModal/ConfirmationModal';
import { usePublishWorkflowCompanion } from '../../../contexts/workflowCompanion';
import { WizardStepFields } from './WizardStepFields';
import { WizardReviewStep } from './WizardReviewStep';
import type {
  WizardProps,
  WizardFormValues,
  WorkflowDefinitionSchema,
  WorkflowRunSchema,
  PreviewResponse,
  WorkflowErrorPayload
} from './types';

function makeIdempotencyKey(runId: number): string {
  const cryptoObj = globalThis.crypto;
  const random =
    cryptoObj && typeof cryptoObj.randomUUID === 'function'
      ? cryptoObj.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `run-${runId}-${random}`;
}

function parseWorkflowError(err: unknown): { status?: number; payload: WorkflowErrorPayload } {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status;
    const data = err.response?.data as Record<string, unknown> | undefined;
    if (data && typeof data === 'object') {
      const detail = data.detail;
      return {
        status,
        payload: {
          message: (data.message as string | undefined) ?? (typeof detail === 'string' ? detail : undefined),
          code: data.code as string | undefined,
          errors: data.errors as Record<string, string> | undefined
        }
      };
    }
    return { status, payload: { message: err.message } };
  }
  return { payload: { message: 'Something went wrong. Please try again.' } };
}

function initialIndex(definition: WorkflowDefinitionSchema, run: WorkflowRunSchema): number {
  if (!run.current_step) return 0;
  const index = definition.steps.findIndex(step => step.id === run.current_step);
  return index >= 0 ? index : 0;
}

function seedFormValues(run: WorkflowRunSchema): WizardFormValues {
  const merged: WizardFormValues = {};
  run.step_states.forEach(state => {
    if (state.inputs) Object.assign(merged, state.inputs);
  });
  return merged;
}

export const Wizard: React.FC<WizardProps> = ({
  definition,
  run,
  onSaveStep,
  onPreview,
  onExecute,
  onExecuteFile,
  onReloadRun,
  onComplete,
  onExit,
  confirmLabel = 'Confirm',
  notify
}) => {
  // Hold a live copy of the definition so context-dependent (cascading) options can refresh after
  // each save via onReloadRun. Seeded from the prop; re-synced only when the prop identity changes
  // (the page mounts the wizard with a stable object, so this fires once and never clobbers reloads).
  const [liveDefinition, setLiveDefinition] = useState<WorkflowDefinitionSchema>(definition);
  const [activeIndex, setActiveIndex] = useState<number>(() => initialIndex(definition, run));
  const [formValues, setFormValues] = useState<WizardFormValues>(() => seedFormValues(run));
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [stepServerErrors, setStepServerErrors] = useState<Record<string, string> | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<WorkflowErrorPayload | null>(null);
  const [reconfirm, setReconfirm] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [exitOpen, setExitOpen] = useState(false);
  const idempotencyKeyRef = useRef<string>(makeIdempotencyKey(run.id));

  const steps = liveDefinition.steps;
  const activeStep = steps[activeIndex];

  // Publish an advisory snapshot of THIS run/step so the read-only assistant can enter Workflow
  // Companion Mode while the wizard is mounted (cleared on unmount). Identifiers only — never the
  // collected form values, the selected file, or the confirm token. The assistant reads run truth
  // server-side via its owner-scoped read-only tool; it never executes anything here.
  usePublishWorkflowCompanion({
    runId: run.id,
    workflowId: run.workflow_id ?? null,
    stepId: activeStep?.id ?? null,
    stepIndex: activeIndex,
    totalSteps: steps.length
  });

  // Re-seed only when a fresh definition object is mounted (stable prop ⇒ runs once). Reloads from
  // onReloadRun set liveDefinition directly and never change the prop, so they are preserved.
  useEffect(() => {
    setLiveDefinition(definition);
  }, [definition]);

  const runPreview = useCallback(
    async (stepId: string) => {
      setPreviewLoading(true);
      setPreviewError(null);
      try {
        const result = await onPreview(stepId);
        setPreview(result);
      } catch (err) {
        const { payload } = parseWorkflowError(err);
        setPreview(null);
        setPreviewError(payload);
      } finally {
        setPreviewLoading(false);
      }
    },
    [onPreview]
  );

  // Build the preview as soon as a write step becomes active; reset any per-step file selection.
  useEffect(() => {
    setSelectedFile(null);
    if (activeStep && activeStep.kind === 'execute') {
      setReconfirm(false);
      runPreview(activeStep.id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeIndex]);

  const cleanInputs = (values: Record<string, string>): WizardFormValues => {
    const cleaned: WizardFormValues = {};
    Object.entries(values).forEach(([key, value]) => {
      if (value !== '' && value !== null && value !== undefined) cleaned[key] = value;
    });
    return cleaned;
  };

  const handleStepSubmit = async (values: Record<string, string>) => {
    if (!activeStep) return;
    setSaving(true);
    setStepServerErrors(null);
    try {
      const state = await onSaveStep(activeStep.id, cleanInputs(values));
      setFormValues(prev => ({ ...prev, ...values }));
      if (state.validation_status === 'invalid') {
        setStepServerErrors(state.validation_errors ?? { _: 'Some details are invalid.' });
        return;
      }
      // Refresh the run so the next step's context-dependent options reflect this selection
      // (e.g. project → documents → files). Best-effort: keep current options if the refresh fails.
      if (onReloadRun) {
        try {
          const refreshed = await onReloadRun();
          setLiveDefinition(refreshed.definition);
          setFormValues(prev => ({ ...prev, ...seedFormValues(refreshed.run) }));
        } catch {
          /* keep existing options rather than blocking progress */
        }
      }
      setActiveIndex(index => Math.min(index + 1, steps.length - 1));
    } catch (err) {
      const { payload } = parseWorkflowError(err);
      const message = payload.message ?? 'Could not save your changes.';
      setStepServerErrors({ _: message });
      notify?.(message);
    } finally {
      setSaving(false);
    }
  };

  const handleBack = () => {
    setPreview(null);
    setPreviewError(null);
    setReconfirm(false);
    setActiveIndex(index => Math.max(index - 1, 0));
  };

  const handleConfirm = async () => {
    if (!activeStep || !preview) return;
    const multipartField = activeStep.multipart_file_field;
    if (multipartField && (!onExecuteFile || !selectedFile)) {
      notify?.('Please choose a file to upload before continuing.');
      return;
    }
    setExecuting(true);
    try {
      const result =
        multipartField && onExecuteFile && selectedFile
          ? await onExecuteFile(activeStep.id, preview.confirm_token, idempotencyKeyRef.current, selectedFile)
          : await onExecute(activeStep.id, preview.confirm_token, idempotencyKeyRef.current);
      onComplete(result);
    } catch (err) {
      const { status, payload } = parseWorkflowError(err);
      if (status === 409 && payload.code === 'reconfirm_required') {
        setReconfirm(true);
        await runPreview(activeStep.id);
        notify?.(payload.message ?? 'Please review the details again.');
      } else {
        const message = payload.message ?? 'Could not complete this step.';
        setPreviewError(payload.message ? payload : { message });
        notify?.(message);
      }
    } finally {
      setExecuting(false);
    }
  };

  return (
    <Paper elevation={0} sx={{ p: { xs: 2, sm: 4 }, border: 1, borderColor: 'divider', borderRadius: 2 }}>
      <Typography variant="h5" fontWeight={600} sx={{ mb: 0.5 }}>
        {liveDefinition.title}
      </Typography>
      {liveDefinition.description && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          {liveDefinition.description}
        </Typography>
      )}

      <Stepper activeStep={activeIndex} alternativeLabel sx={{ mb: 4 }}>
        {steps.map(step => (
          <Step key={step.id}>
            <StepLabel>{step.title}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {activeStep?.kind === 'collect' ? (
        <WizardStepFields
          key={activeStep.id}
          step={activeStep}
          initialValues={formValues}
          saving={saving}
          serverErrors={stepServerErrors}
          onSubmit={handleStepSubmit}
          onExit={() => setExitOpen(true)}
        />
      ) : activeStep ? (
        <WizardReviewStep
          step={activeStep}
          preview={preview}
          previewLoading={previewLoading}
          previewError={previewError}
          reconfirm={reconfirm}
          executing={executing}
          confirmLabel={confirmLabel}
          multipartFileField={activeStep.multipart_file_field}
          selectedFile={selectedFile}
          onFileChange={setSelectedFile}
          onConfirm={handleConfirm}
          onBack={handleBack}
          onExit={() => setExitOpen(true)}
        />
      ) : null}

      <ConfirmationModal
        open={exitOpen}
        confirmationTitle="Discard this workflow?"
        confirmationMessage="Your progress will be discarded and the workflow will be cancelled. This cannot be undone."
        confirmationDisabled={false}
        onConfirm={() => {
          setExitOpen(false);
          onExit();
        }}
        onClose={() => setExitOpen(false)}
      />
    </Paper>
  );
};

export default Wizard;

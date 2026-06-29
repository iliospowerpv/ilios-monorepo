import type {
  WorkflowDefinitionSchema,
  WorkflowRunSchema,
  WorkflowStepStateSchema,
  PreviewResponse,
  ExecuteResponse
} from '../../../api/workflows';

export type {
  WorkflowDefinitionSchema,
  WorkflowStepSchema,
  WorkflowFieldSchema,
  WorkflowFieldOption,
  WorkflowRunSchema,
  WorkflowStepStateSchema,
  PreviewResponse,
  PreviewItem,
  ExecuteResponse,
  WorkflowErrorPayload
} from '../../../api/workflows';

// All wizard inputs are collected as strings (text / select); the backend re-validates
// against the EXISTING domain schema.
export type WizardFormValues = Record<string, unknown>;

export interface WizardProps {
  definition: WorkflowDefinitionSchema;
  run: WorkflowRunSchema;
  // Persist + server-validate a collect step's inputs. Returns the saved step state so the
  // shell can surface per-field validation without owning truth.
  onSaveStep: (stepId: string, inputs: WizardFormValues) => Promise<WorkflowStepStateSchema>;
  // Build a read-only preview + confirm token for a write step (no mutation).
  onPreview: (stepId: string) => Promise<PreviewResponse>;
  // Execute a confirmed write step via the EXISTING endpoint behind the confirm token.
  onExecute: (stepId: string, confirmToken: string, idempotencyKey: string) => Promise<ExecuteResponse>;
  onComplete: (result: ExecuteResponse) => void;
  onExit: () => void;
  confirmLabel?: string;
  notify?: (message: string) => void;
}

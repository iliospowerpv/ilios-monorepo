import type {
  WorkflowDefinitionSchema,
  WorkflowRunSchema,
  WorkflowRunDetailResponse,
  WorkflowStepStateSchema,
  PreviewResponse,
  ExecuteResponse
} from '../../../api/workflows';

export type {
  WorkflowDefinitionSchema,
  WorkflowStepSchema,
  WorkflowFieldSchema,
  WorkflowFieldOption,
  WorkflowPrerequisiteSchema,
  WorkflowRunSchema,
  WorkflowRunDetailResponse,
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
  // Optional multipart execute for an EXECUTE step declaring `multipart_file_field`. When present
  // the shell renders a file input on the review step and dispatches via this instead of onExecute.
  onExecuteFile?: (
    stepId: string,
    confirmToken: string,
    idempotencyKey: string,
    file: File
  ) => Promise<ExecuteResponse>;
  // Optional: re-fetch the run + (re-serialized) definition after each collect step saves so
  // context-dependent (cascading) options refresh. Omitted by static flows (add_company / add_site),
  // whose options never depend on prior selections — their behavior is unchanged.
  onReloadRun?: () => Promise<WorkflowRunDetailResponse>;
  onComplete: (result: ExecuteResponse) => void;
  onExit: () => void;
  confirmLabel?: string;
  notify?: (message: string) => void;
}

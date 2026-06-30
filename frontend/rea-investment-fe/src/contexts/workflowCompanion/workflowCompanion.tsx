import React, { createContext, useContext, useState, useMemo, useEffect } from 'react';

// Advisory, read-only snapshot of the guided workflow run the user is currently inside. It is
// published by the shared <Wizard> shell and consumed by the AssistantWidget so the read-only
// assistant can enter "Workflow Companion Mode" (explain the step/fields/validation/confirmation,
// resume guidance, blockers). It NEVER carries form values, selected files, or confirm tokens —
// only the run/step identifiers the server already owns. The assistant still resolves every real
// answer through its authz-scoped read-only tools and never executes anything.
export interface WorkflowCompanionState {
  runId: number;
  workflowId: string | null;
  stepId: string | null;
  stepIndex: number | null;
  totalSteps: number | null;
}

interface WorkflowCompanionContextType {
  companion: WorkflowCompanionState | null;
  setCompanion: (state: WorkflowCompanionState | null) => void;
}

const WorkflowCompanionContext = createContext<WorkflowCompanionContextType | undefined>(undefined);

export const WorkflowCompanionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [companion, setCompanion] = useState<WorkflowCompanionState | null>(null);

  const value = useMemo(() => ({ companion, setCompanion }), [companion]);

  return <WorkflowCompanionContext.Provider value={value}>{children}</WorkflowCompanionContext.Provider>;
};

export const useWorkflowCompanion = (): WorkflowCompanionContextType => {
  const context = useContext(WorkflowCompanionContext);
  if (context === undefined) {
    throw new Error('useWorkflowCompanion must be used within a WorkflowCompanionProvider');
  }
  return context;
};

// Publisher used by the <Wizard> shell: mirrors the active run/step into the shared context while
// the wizard is mounted and clears it on unmount (so the assistant only enters Companion Mode while
// the user is genuinely inside a run). Depends on the primitive fields so it re-publishes exactly
// when the step changes, never on every render.
export const usePublishWorkflowCompanion = (state: WorkflowCompanionState | null): void => {
  const { setCompanion } = useWorkflowCompanion();
  const runId = state?.runId ?? null;
  const workflowId = state?.workflowId ?? null;
  const stepId = state?.stepId ?? null;
  const stepIndex = state?.stepIndex ?? null;
  const totalSteps = state?.totalSteps ?? null;

  useEffect(() => {
    if (runId == null) {
      setCompanion(null);
      return;
    }
    setCompanion({ runId, workflowId, stepId, stepIndex, totalSteps });
    return () => setCompanion(null);
  }, [setCompanion, runId, workflowId, stepId, stepIndex, totalSteps]);
};

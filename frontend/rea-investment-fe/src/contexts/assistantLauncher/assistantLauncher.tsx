import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';

// Bounded set of places that can open the assistant. This runtime tuple is the SINGLE source of
// truth for the entry-source vocabulary; the `AssistantEntrySource` union below is derived from it so
// the type and the runtime list can never drift apart. It MUST stay in sync with the server-side
// `_ENTRY_SOURCES` allowlist (backend `app/services/assistant/ui_events_service.py`) for the
// `discoverability_entry_clicked` event — a drift test on each side pins this exact list.
export const ASSISTANT_ENTRY_SOURCES = ['topbar', 'help_menu', 'sidebar', 'empty_state', 'module_header'] as const;
export type AssistantEntrySource = (typeof ASSISTANT_ENTRY_SOURCES)[number];

// A monotonic open request. The id lets the widget react to repeated requests from the same source
// (each click bumps the id) without needing a callback registration.
export interface AssistantOpenRequest {
  id: number;
  source: AssistantEntrySource | null;
}

interface AssistantLauncherContextType {
  // True only while the read-only assistant is actually reachable (flag on + authenticated). Entry
  // points outside the widget read this so they never render a dead button.
  available: boolean;
  setAvailable: (value: boolean) => void;
  openRequest: AssistantOpenRequest | null;
  // Ask the (single, already-mounted) assistant drawer to open. Purely navigational — opening the
  // drawer is the ONLY effect; it never executes, previews, or starts anything.
  requestOpen: (source?: AssistantEntrySource | null) => void;
}

// Stable no-op used when no provider is mounted (e.g. unauthenticated layouts that do not render the
// assistant). A constant identity keeps consumer effects from re-firing.
const NOOP_LAUNCHER: AssistantLauncherContextType = {
  available: false,
  setAvailable: () => undefined,
  openRequest: null,
  requestOpen: () => undefined
};

const AssistantLauncherContext = createContext<AssistantLauncherContextType | undefined>(undefined);

// Shared, app-wide handle to the single AI Assistant drawer. Lets global chrome (top bar, help menu)
// open the existing read-only drawer instead of spawning a second instance or a second code path.
export const AssistantLauncherProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [available, setAvailable] = useState(false);
  const [openRequest, setOpenRequest] = useState<AssistantOpenRequest | null>(null);

  const requestOpen = useCallback((source: AssistantEntrySource | null = null) => {
    setOpenRequest(prev => ({ id: (prev?.id ?? 0) + 1, source }));
  }, []);

  const value = useMemo(
    () => ({ available, setAvailable, openRequest, requestOpen }),
    [available, openRequest, requestOpen]
  );

  return <AssistantLauncherContext.Provider value={value}>{children}</AssistantLauncherContext.Provider>;
};

// Non-throwing consumer: returns a stable no-op when used outside the provider so entry points placed
// in shared chrome never crash if rendered without the authenticated shell.
export const useAssistantLauncher = (): AssistantLauncherContextType => {
  const context = useContext(AssistantLauncherContext);
  return context ?? NOOP_LAUNCHER;
};

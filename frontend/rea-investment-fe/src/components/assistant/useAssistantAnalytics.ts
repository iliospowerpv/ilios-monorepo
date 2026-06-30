import * as React from 'react';

import { ApiClient } from '../../api';
import type { AssistantUiEventIn, AssistantUiEventName } from '../../api/assistant';

// How long to coalesce buffered events before flushing a batch (ms). Short enough that a quick
// open→close still reports before the page may go away, long enough to coalesce bursts.
const FLUSH_DELAY_MS = 3000;
// Hard cap mirrored from the server (batch max 50); flush immediately once reached.
const MAX_BATCH = 50;

export interface TrackOptions {
  // Small, per-event allowlisted qualifier (e.g. an action card's kind). Server strips anything off
  // the per-event allowlist, so an over-eager value is simply dropped, never stored verbatim.
  detail?: string | null;
  // Raw client route; defaults to the current pathname. The server reduces it to a coarse bucket.
  route?: string | null;
  // Whether the interaction happened inside a guided workflow wizard (companion mode).
  inCompanion?: boolean;
}

export interface AssistantAnalytics {
  track: (event: AssistantUiEventName, opts?: TrackOptions) => void;
}

// First-party, privacy-bounded UI-interaction analytics for the AI Assistant.
//
// Design goals (Task #89):
//  - Best-effort & invisible: buffered, debounced, fire-and-forget. A failed/disabled endpoint or an
//    offline client NEVER throws into the UI (the api layer swallows errors).
//  - Bounded payloads only: a fixed event-name enum + coarse route + a small allowlisted detail
//    token + an in-companion flag. NEVER message/reply content or any business value.
//  - No retries / no local persistence: this is adoption telemetry, not operational truth, so a lost
//    batch is acceptable. We flush on a debounce timer, on tab-hide (visibilitychange→hidden, while
//    the page is still alive), and on unmount.
//  - Inert when disabled: when `enabled` is false (assistant flag off / signed out) `track` is a
//    no-op and nothing is buffered or sent.
export const useAssistantAnalytics = (enabled: boolean): AssistantAnalytics => {
  const bufferRef = React.useRef<AssistantUiEventIn[]>([]);
  const timerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  // Keep the latest `enabled` readable from stable callbacks without re-creating them.
  const enabledRef = React.useRef(enabled);
  enabledRef.current = enabled;

  const flush = React.useCallback(() => {
    if (timerRef.current != null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (bufferRef.current.length === 0) return;
    const batch = bufferRef.current;
    bufferRef.current = [];
    // Fire-and-forget: the api method never rejects, so nothing here can surface to the user.
    void ApiClient.assistant.trackEvents(batch);
  }, []);

  const track = React.useCallback(
    (event: AssistantUiEventName, opts: TrackOptions = {}) => {
      if (!enabledRef.current) return;
      bufferRef.current.push({
        event,
        route:
          opts.route ?? (typeof window !== 'undefined' ? window.location.pathname : null),
        detail: opts.detail ?? null,
        in_companion: opts.inCompanion ?? false
      });
      if (bufferRef.current.length >= MAX_BATCH) {
        flush();
        return;
      }
      if (timerRef.current == null) {
        timerRef.current = setTimeout(flush, FLUSH_DELAY_MS);
      }
    },
    [flush]
  );

  React.useEffect(() => {
    const handleVisibility = () => {
      // Flush while the page is still alive (tab hidden / backgrounded) — the most reliable point to
      // get buffered events out before a potential navigation/close.
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
        flush();
      }
    };
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', handleVisibility);
    }
    return () => {
      if (typeof document !== 'undefined') {
        document.removeEventListener('visibilitychange', handleVisibility);
      }
      flush();
    };
  }, [flush]);

  return { track };
};

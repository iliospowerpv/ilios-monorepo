import { useCallback, useEffect, useState } from 'react';

export interface TelemetryCooldown {
  /** Whole seconds until the shared manual refresh/catch-up cooldown clears. */
  secondsRemaining: number;
  /** True while a manual refresh or catch-up is still cooling down. */
  isCoolingDown: boolean;
  /**
   * Arm (or extend) the cooldown by `seconds`. No-op for non-positive values.
   * Always keeps the later expiry (max), so a catch-up can never shorten a
   * refresh cooldown or vice-versa — they share one per-project window.
   */
  startCooldown: (seconds: number) => void;
}

/**
 * Drives the shared per-project manual refresh/catch-up cooldown countdown.
 *
 * The backend is the source of truth: it enforces the real cooldown (HTTP 429 +
 * `Retry-After`) and reports the remaining window on every manual response
 * (`cooldown_seconds`). This hook only mirrors that in the UI so the Refresh and
 * Catch-up controls disable themselves and show a live countdown. State is
 * intentionally lifted to the Telemetry tab and shared by both controls because
 * the cooldown itself is shared on the server.
 */
export const useTelemetryCooldown = (): TelemetryCooldown => {
  const [until, setUntil] = useState(0);
  const [now, setNow] = useState(() => Date.now());

  const startCooldown = useCallback((seconds: number) => {
    if (!Number.isFinite(seconds) || seconds <= 0) return;
    const expiry = Date.now() + Math.ceil(seconds) * 1000;
    setUntil(prev => Math.max(prev, expiry));
    setNow(Date.now());
  }, []);

  const secondsRemaining = Math.max(0, Math.ceil((until - now) / 1000));
  const isCoolingDown = secondsRemaining > 0;

  // Tick once a second only while a cooldown is active; the effect tears the
  // interval down as soon as the countdown reaches zero.
  useEffect(() => {
    if (!isCoolingDown) return undefined;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [isCoolingDown]);

  return { secondsRemaining, isCoolingDown, startCooldown };
};

/** Human-readable countdown, e.g. "4m 12s" or "45s". */
export const formatCooldown = (seconds: number): string => {
  const safe = Math.max(0, Math.floor(seconds));
  const mins = Math.floor(safe / 60);
  const secs = safe % 60;
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
};

/**
 * Pull the `Retry-After` value (seconds) out of an axios 429 error, or return
 * null when the error is not a cooldown rejection or carries no usable header.
 * Axios lower-cases response header keys, so we read `retry-after`.
 */
export const parseRetryAfterSeconds = (err: unknown): number | null => {
  const e = err as { response?: { status?: number; headers?: Record<string, unknown> } };
  if (e?.response?.status !== 429) return null;
  const raw = e.response.headers?.['retry-after'];
  const seconds = typeof raw === 'string' ? parseInt(raw, 10) : typeof raw === 'number' ? raw : NaN;
  return Number.isFinite(seconds) && seconds > 0 ? seconds : null;
};

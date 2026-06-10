/**
 * The telemetry backend stores and serializes naive UTC timestamps (no timezone
 * designator, e.g. "2026-06-10T14:30:00"). `new Date(...)` would interpret those
 * as LOCAL time, throwing off "is the lock still held?" and "next due" math by
 * the browser's UTC offset. These helpers normalize a missing designator to `Z`
 * so the value is always parsed as UTC.
 */

const hasTimezone = (iso: string): boolean => /([zZ])$|([+-]\d{2}:?\d{2})$/.test(iso.trim());

/** Parse an ISO string as UTC, returning `null` for empty/invalid input. */
export const parseUtc = (iso: string | null | undefined): Date | null => {
  if (!iso) return null;
  const normalized = hasTimezone(iso) ? iso : `${iso}Z`;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
};

/** Format an ISO (naive-UTC) timestamp in the viewer's locale, or a fallback. */
export const formatUtc = (iso: string | null | undefined, fallback = 'Never'): string => {
  const date = parseUtc(iso);
  return date ? date.toLocaleString() : fallback;
};

/** True when the given lock timestamp is in the future (a run is in progress). */
export const isLockActive = (lockedUntil: string | null | undefined): boolean => {
  const date = parseUtc(lockedUntil);
  return !!date && date.getTime() > Date.now();
};

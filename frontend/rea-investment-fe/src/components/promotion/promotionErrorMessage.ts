/** Umbrella error_code the backend sends when the freshness guard fails closed. */
export const PROMOTION_SOURCE_STALE_CODE = 'PROMOTION_SOURCE_STALE';

/**
 * Map a failed promote request to an honest, user-facing message.
 *
 * Two backend error shapes are handled:
 * - Freshness-guard failures fail closed as HTTP 409 with a machine-readable
 *   *top-level* body (`{ error_code: 'PROMOTION_SOURCE_STALE', message, stale_fields }`,
 *   returned as a `JSONResponse` so it is NOT collapsed into `detail`). The
 *   backend `message` already names the stale-value count and steers the user
 *   to the Data Room, so we surface it verbatim (with a safe fallback).
 * - Every other `PromotionError` is HTTP 400 with a human `detail` string (no
 *   code), so we match on status + message text. A stale/mismatched version
 *   means it is no longer valid; everything else means the atomic promotion
 *   rolled back and nothing changed.
 *
 * Lives in the shared promotion module so both the Reconciliation and Data Room
 * launchers (and `Reconciliation/utils`, which re-exports it) share one source.
 */
export const promotionErrorMessage = (error: unknown): string => {
  const axiosError = error as {
    response?: {
      status?: number;
      data?: { detail?: string; error_code?: string; message?: string };
    };
  };
  const status = axiosError?.response?.status;
  const data = axiosError?.response?.data;
  const detail = data?.detail ?? '';

  if (status === 403) {
    return 'You do not have permission to promote assumptions for this project.';
  }
  // Fail-closed freshness guard: surface the backend's specific, actionable
  // message (it already mentions re-reviewing in the Data Room).
  if (status === 409 && data?.error_code === PROMOTION_SOURCE_STALE_CODE) {
    return (
      data?.message ??
      'Some accepted values are out of date with the latest parse of this version. ' +
        'Re-review them in the Data Room before promoting.'
    );
  }
  if (status === 404 || /file not found/i.test(detail) || /does not belong/i.test(detail)) {
    return 'This version is no longer valid for promotion; refresh and try again.';
  }
  return 'Promotion failed and nothing was changed.';
};

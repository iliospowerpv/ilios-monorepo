/**
 * Map a failed promote request to an honest, user-facing message. The backend
 * raises every `PromotionError` as HTTP 400 with a human `detail` string (not a
 * code), so we match on status + message text. Validation mismatches mean the
 * version is stale; everything else means the atomic promotion rolled back and
 * nothing changed.
 *
 * Lives in the shared promotion module so both the Reconciliation and Data Room
 * launchers (and `Reconciliation/utils`, which re-exports it) share one source.
 */
export const promotionErrorMessage = (error: unknown): string => {
  const axiosError = error as { response?: { status?: number; data?: { detail?: string } } };
  const status = axiosError?.response?.status;
  const detail = axiosError?.response?.data?.detail ?? '';

  if (status === 403) {
    return 'You do not have permission to promote assumptions for this project.';
  }
  if (status === 404 || /file not found/i.test(detail) || /does not belong/i.test(detail)) {
    return 'This version is no longer valid for promotion; refresh and try again.';
  }
  return 'Promotion failed and nothing was changed.';
};

/**
 * Context for a single file-version promotion, independent of where it was
 * launched. Promotion is always file-version-scoped and all-or-nothing — these
 * ids identify the version, and the optional fields are display-only metadata
 * surfaced in the dialog so the user can confirm exactly which document version
 * they are promoting.
 */
export interface PromoteVersionContext {
  /** Backend document id (promote payload `document_id`). */
  documentId: number;
  /** File-version id (promote payload `file_id`; diff/candidates cache key). */
  fileId: number;
  /**
   * Field label the user launched from (Reconciliation). When present the scope
   * warning names it ("not just X") and the diff highlights it. Absent for
   * whole-version launches (e.g. the Data Room), where no single field is implied.
   */
  launchedFieldLabel?: string | null;
  /** Optional human document title/name. */
  documentName?: string | null;
  /** Optional document-type label (e.g. "PPA"). */
  documentTypeLabel?: string | null;
  /** Optional source file name. */
  fileName?: string | null;
  /** Optional version label. */
  versionLabel?: string | null;
  /** Optional upload timestamp (ISO string). */
  uploadedAt?: string | null;
  /** Optional "actual / final" marker for the file version. */
  isActual?: boolean | null;
}

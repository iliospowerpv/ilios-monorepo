// Shared, PURE display mappers for the weather-adjusted expected-baseline
// fail-closed validation verdict (Phase B2). This module renders the verdict the
// backend engine already produced — it computes NOTHING about physics, changes
// no rule, and never re-derives a classification. Every consumer (the grouped
// validation panel, the activation-readiness summary, the review panel's chips)
// maps from the SAME helpers so severity wording/colors stay consistent.
//
// Honesty rules carried over from the operational truth-store:
//   - A null/absent verdict is `unavailable` (neutral) — never coloured as
//     valid OR invalid, never shown as 0/0%.
//   - A field classification is mapped strictly from the engine's
//     `classification`; an unknown value is neutral, never guessed into a
//     warning/blocking colour.

import type { BaselinePhysicsValidation, BaselineValidationFieldVerdict } from '../types/telemetryV2';

export type MuiSeverityColor = 'default' | 'info' | 'primary' | 'success' | 'warning' | 'error';

// The explicit reviewer-facing state vocabulary (audit §14 B2.2). The validation
// verdict itself only ever resolves to the subset
// {unavailable, blocked, warning, ready}; the remaining terms exist so chips
// stay consistent if a caller reuses the metadata for readiness/partial states.
export type BaselineValidationState =
  | 'ready'
  | 'available'
  | 'warning'
  | 'needs_review'
  | 'partial'
  | 'blocked'
  | 'invalid'
  | 'unavailable';

export interface ValidationStateMeta {
  state: BaselineValidationState;
  label: string;
  color: MuiSeverityColor;
  // Lower number = more urgent. Used to sort/rank states deterministically.
  severityRank: number;
  description: string;
}

// Deterministic severity ordering: blocked/invalid (1) is most urgent, a
// fully-ready verdict (6) least. `needs_review`/`partial`/`unavailable` sit in
// between so a grouped view always orders the same way.
const STATE_META: Record<BaselineValidationState, ValidationStateMeta> = {
  blocked: {
    state: 'blocked',
    label: 'Blocked',
    color: 'error',
    severityRank: 1,
    description: 'A hard-invalid physics value is present. This baseline cannot be activated until it is replaced.'
  },
  invalid: {
    state: 'invalid',
    label: 'Invalid',
    color: 'error',
    severityRank: 1,
    description:
      'The baseline failed fail-closed physics validation, so expected production is suppressed (N/A, never 0).'
  },
  warning: {
    state: 'warning',
    label: 'Valid with warnings',
    color: 'warning',
    severityRank: 2,
    description: 'No blocking values, but one or more inputs need confirmation before activation (with a source note).'
  },
  needs_review: {
    state: 'needs_review',
    label: 'Needs review',
    color: 'warning',
    severityRank: 3,
    description: 'A human decision is required before this value can advance.'
  },
  partial: {
    state: 'partial',
    label: 'Partial',
    color: 'info',
    severityRank: 4,
    description: 'Only part of the required inputs are present; coverage is incomplete.'
  },
  unavailable: {
    state: 'unavailable',
    label: 'Not evaluated',
    color: 'default',
    severityRank: 5,
    description: 'No validation verdict is available for this baseline.'
  },
  ready: {
    state: 'ready',
    label: 'Valid',
    color: 'success',
    severityRank: 6,
    description: 'All physics inputs are plausible. No blocking values and no warnings to acknowledge.'
  },
  available: {
    state: 'available',
    label: 'Available',
    color: 'success',
    severityRank: 6,
    description: 'Expected production can be computed normally.'
  }
};

export const validationStateMeta = (state: BaselineValidationState): ValidationStateMeta => STATE_META[state];

/**
 * Map a fail-closed physics verdict to a single explicit state. A null/absent
 * verdict is `unavailable` (neutral) — never coloured valid or invalid.
 * `is_blocking` wins; then warnings; otherwise `ready`.
 */
export const resolveValidationState = (v: BaselinePhysicsValidation | null | undefined): ValidationStateMeta => {
  if (!v) return STATE_META.unavailable;
  if (v.is_blocking) return STATE_META.blocked;
  const warningCount = v.warning_field_count ?? (v.has_warnings ? 1 : 0);
  if (warningCount > 0 || v.has_warnings) return STATE_META.warning;
  return STATE_META.ready;
};

// ---------------------------------------------------------------------------
// Per-field classification mapping (strict — never guesses).
// ---------------------------------------------------------------------------

export type FieldClassificationKind = 'blocking' | 'warning' | 'plausible' | 'neutral';

/**
 * Map the engine's `classification` string to a coarse kind. `hard_invalid` is
 * blocking; `warning`/`implausible` are warnings; `plausible` is fine; anything
 * unrecognised is neutral (never inflated to a warning).
 */
export const classificationKind = (classification: string | null | undefined): FieldClassificationKind => {
  switch (classification) {
    case 'hard_invalid':
      return 'blocking';
    case 'warning':
    case 'implausible':
      return 'warning';
    case 'plausible':
      return 'plausible';
    default:
      return 'neutral';
  }
};

export const classificationColor = (classification: string | null | undefined): MuiSeverityColor => {
  switch (classificationKind(classification)) {
    case 'blocking':
      return 'error';
    case 'warning':
      return 'warning';
    case 'plausible':
      return 'success';
    default:
      return 'default';
  }
};

export const classificationLabel = (classification: string | null | undefined): string => {
  if (!classification) return 'Not evaluated';
  return classification.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
};

export interface GroupedFieldVerdicts {
  blocking: BaselineValidationFieldVerdict[];
  warning: BaselineValidationFieldVerdict[];
  plausible: BaselineValidationFieldVerdict[];
  blockingCount: number;
  warningCount: number;
  plausibleCount: number;
}

/**
 * Partition the full per-field + cross-field verdicts of a report into
 * blocking / warning / plausible groups (audit §14 B2.1). Returns empty groups
 * when the report carries no `fields[]` (the compact list/active summary).
 */
export const groupFieldVerdicts = (v: BaselinePhysicsValidation | null | undefined): GroupedFieldVerdicts => {
  const all: BaselineValidationFieldVerdict[] = [...(v?.fields ?? []), ...(v?.cross_field_checks ?? [])];
  const blocking = all.filter(f => classificationKind(f.classification) === 'blocking');
  const warning = all.filter(f => classificationKind(f.classification) === 'warning');
  const plausible = all.filter(f => classificationKind(f.classification) === 'plausible');
  return {
    blocking,
    warning,
    plausible,
    blockingCount: blocking.length,
    warningCount: warning.length,
    plausibleCount: plausible.length
  };
};

// ---------------------------------------------------------------------------
// Source-basis labelling (audit §14 B2.5). Maps the `model_parameters_json`
// field-source class to an honest basis label. Reviewer-supplied constants have
// NO document source — never fabricate one.
// ---------------------------------------------------------------------------

export interface SourceBasisMeta {
  label: string;
  color: MuiSeverityColor;
  hasDocumentSource: boolean;
  description: string;
}

export const sourceBasisMeta = (source: string | null | undefined): SourceBasisMeta => {
  switch (source) {
    case 'project_fact':
      return {
        label: 'Fact-backed',
        color: 'success',
        hasDocumentSource: true,
        description: 'Promoted from a source-backed project fact.'
      };
    case 'project_fact_normalized':
      return {
        label: 'Normalized from facts',
        color: 'success',
        hasDocumentSource: true,
        description: 'Promoted from a project fact after a unit normalization.'
      };
    case 'reviewer_supplied':
      return {
        label: 'Reviewer-supplied',
        color: 'info',
        hasDocumentSource: false,
        description: 'A datasheet constant entered by the reviewer — no document source exists.'
      };
    default:
      return {
        label: source ?? 'Unknown source',
        color: 'default',
        hasDocumentSource: false,
        description: 'Source basis is unknown.'
      };
  }
};

// ---------------------------------------------------------------------------
// Activation block-reason explainer (audit §14 B2.6). Context-sensitive copy for
// the three structured-409 reasons. The contract is unchanged — this is purely a
// clearer client explanation.
// ---------------------------------------------------------------------------

export type BaselineBlockReason = 'hard_invalid' | 'warnings_require_ack' | 'source_note_required';

export interface BlockReasonExplainer {
  title: string;
  detail: string;
  waivable: boolean;
}

export const blockReasonExplainer = (reason: string | null | undefined): BlockReasonExplainer | null => {
  switch (reason) {
    case 'hard_invalid':
      return {
        title: 'Physically invalid — cannot be activated',
        detail:
          'One or more values fail fail-closed physics validation. This cannot be waived; create a source-backed replacement baseline with corrected values.',
        waivable: false
      };
    case 'warnings_require_ack':
      return {
        title: 'Confirmation required before activation',
        detail:
          'No blocking values, but some inputs need confirmation. Acknowledge the warnings and add a source note to activate.',
        waivable: true
      };
    case 'source_note_required':
      return {
        title: 'Source note required',
        detail:
          'A source note is required to activate a baseline with acknowledged warnings. Document the source / justification before activating.',
        waivable: true
      };
    default:
      return null;
  }
};

import {
  blockReasonExplainer,
  classificationColor,
  classificationKind,
  classificationLabel,
  groupFieldVerdicts,
  resolveValidationState,
  sourceBasisMeta,
  validationStateMeta
} from '../baselineValidation';
import type { BaselinePhysicsValidation, BaselineValidationFieldVerdict } from '../../types/telemetryV2';

const verdict = (over: Partial<BaselineValidationFieldVerdict>): BaselineValidationFieldVerdict => ({
  field: 'thermal_coefficient_pct',
  entered_value: -0.35,
  expected_unit: '% per °C',
  classification: 'plausible',
  reason: 'ok',
  source: 'facts_promotion',
  required_action: null,
  ...over
});

const report = (over: Partial<BaselinePhysicsValidation>): BaselinePhysicsValidation => ({
  baseline_id: 1,
  is_blocking: false,
  summary: 'summary',
  policy_version: 'baseline-physics-v1',
  ...over
});

describe('resolveValidationState', () => {
  it('maps a null/absent verdict to neutral "unavailable" (never valid/invalid)', () => {
    const meta = resolveValidationState(null);
    expect(meta.state).toBe('unavailable');
    expect(meta.color).toBe('default');
  });

  it('maps a blocking verdict to "blocked" (error)', () => {
    const meta = resolveValidationState(report({ is_blocking: true, blocking_field_count: 1 }));
    expect(meta.state).toBe('blocked');
    expect(meta.color).toBe('error');
  });

  it('maps a non-blocking verdict with warnings to "warning"', () => {
    const meta = resolveValidationState(report({ warning_field_count: 2 }));
    expect(meta.state).toBe('warning');
    expect(meta.color).toBe('warning');
  });

  it('maps a clean verdict to "ready" (success)', () => {
    const meta = resolveValidationState(report({ warning_field_count: 0 }));
    expect(meta.state).toBe('ready');
    expect(meta.color).toBe('success');
  });

  it('treats has_warnings=true as a warning even without a count', () => {
    expect(resolveValidationState(report({ has_warnings: true })).state).toBe('warning');
  });
});

describe('classification mapping', () => {
  it('maps kinds strictly (unknown -> neutral, never inflated)', () => {
    expect(classificationKind('hard_invalid')).toBe('blocking');
    expect(classificationKind('warning')).toBe('warning');
    expect(classificationKind('implausible')).toBe('warning');
    expect(classificationKind('plausible')).toBe('plausible');
    expect(classificationKind('something_else')).toBe('neutral');
    expect(classificationKind(null)).toBe('neutral');
  });

  it('maps colors from kinds', () => {
    expect(classificationColor('hard_invalid')).toBe('error');
    expect(classificationColor('warning')).toBe('warning');
    expect(classificationColor('plausible')).toBe('success');
    expect(classificationColor(undefined)).toBe('default');
  });

  it('humanizes labels and handles absent classification', () => {
    expect(classificationLabel('hard_invalid')).toBe('Hard Invalid');
    expect(classificationLabel(null)).toBe('Not evaluated');
  });
});

describe('groupFieldVerdicts', () => {
  it('returns empty groups for the compact summary (no fields[])', () => {
    const g = groupFieldVerdicts(report({}));
    expect(g.blockingCount).toBe(0);
    expect(g.warningCount).toBe(0);
    expect(g.plausibleCount).toBe(0);
  });

  it('partitions fields + cross_field_checks by classification', () => {
    const g = groupFieldVerdicts(
      report({
        fields: [
          verdict({ field: 'a', classification: 'hard_invalid' }),
          verdict({ field: 'b', classification: 'warning' }),
          verdict({ field: 'c', classification: 'plausible' })
        ],
        cross_field_checks: [verdict({ field: 'x', classification: 'hard_invalid' })]
      })
    );
    expect(g.blockingCount).toBe(2);
    expect(g.warningCount).toBe(1);
    expect(g.plausibleCount).toBe(1);
    expect(g.blocking.map(f => f.field)).toEqual(['a', 'x']);
  });
});

describe('sourceBasisMeta', () => {
  it('labels reviewer-supplied constants as having NO document source', () => {
    const m = sourceBasisMeta('reviewer_supplied');
    expect(m.hasDocumentSource).toBe(false);
    expect(m.label).toMatch(/Reviewer/i);
  });

  it('labels fact-backed sources as having a document source', () => {
    expect(sourceBasisMeta('project_fact').hasDocumentSource).toBe(true);
    expect(sourceBasisMeta('project_fact_normalized').hasDocumentSource).toBe(true);
  });

  it('falls back honestly for an unknown source', () => {
    expect(sourceBasisMeta(undefined).label).toBe('Unknown source');
  });
});

describe('blockReasonExplainer', () => {
  it('marks hard_invalid as NOT waivable', () => {
    expect(blockReasonExplainer('hard_invalid')?.waivable).toBe(false);
  });

  it('marks warning reasons as waivable', () => {
    expect(blockReasonExplainer('warnings_require_ack')?.waivable).toBe(true);
    expect(blockReasonExplainer('source_note_required')?.waivable).toBe(true);
  });

  it('returns null for an unknown reason', () => {
    expect(blockReasonExplainer('nope')).toBeNull();
  });
});

describe('validationStateMeta severity ranking', () => {
  it('ranks blocked above warning above ready', () => {
    expect(validationStateMeta('blocked').severityRank).toBeLessThan(validationStateMeta('warning').severityRank);
    expect(validationStateMeta('warning').severityRank).toBeLessThan(validationStateMeta('ready').severityRank);
  });
});

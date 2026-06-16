import {
  OVERVIEW_FIELD_TO_RECON,
  buildReconciliationIndex,
  resolveReconciliationRow,
  resolveProtectedValue
} from '../reconciliationFieldMap';
import type { ReconciliationRow } from '../../../../../../../../../api';

const makeRow = (overrides: Partial<ReconciliationRow>): ReconciliationRow =>
  ({
    canonical_field: 'x',
    display_label: 'X',
    category: 'baseline_physics',
    baseline_target: 'header_column',
    status: 'missing',
    status_label: null,
    status_explanation: null,
    required_action: null,
    blocking_level: null,
    missing_dependencies: [],
    ai_extracted_value: null,
    accepted_value: null,
    active_fact_value: null,
    draft_baseline_value: null,
    active_baseline_value: null,
    legacy_value: null,
    fact_id: null,
    project_fact_id: null,
    source_file_id: null,
    source_document_type: null,
    source_run_id: null,
    evidence_page: null,
    evidence_snippet: null,
    confidence: null,
    effective_from: null,
    effective_to: null,
    document_id: null,
    document_version_id: null,
    ai_run_id: null,
    document_key_id: null,
    baseline_id: null,
    baseline_point_id: null,
    aliases_matched: [],
    supersedes_fact_id: null,
    candidate_count: 0,
    required_for_baseline: false,
    warnings: [],
    ...overrides
  } as ReconciliationRow);

describe('reconciliationFieldMap — buildReconciliationIndex / resolveReconciliationRow', () => {
  it('indexes by canonical_field and aliases, case-insensitively', () => {
    const rows = [
      makeRow({ canonical_field: 'dc_loss_pct', aliases_matched: ['DC Ohmic Loss'] }),
      makeRow({ canonical_field: 'pto_date' })
    ];
    const index = buildReconciliationIndex(rows);

    // canonical key (lowercased)
    expect(resolveReconciliationRow(index, 'dc_wiring_loss')?.canonical_field).toBe('dc_loss_pct');
    // alias hit via case-insensitive normalization
    expect(index.get('dc ohmic loss')?.canonical_field).toBe('dc_loss_pct');
    // a mapped field resolving to its canonical
    expect(resolveReconciliationRow(index, 'permission_to_operate')?.canonical_field).toBe('pto_date');
  });

  it('returns undefined when no row matches (graceful degrade)', () => {
    const index = buildReconciliationIndex([makeRow({ canonical_field: 'pto_date' })]);
    expect(resolveReconciliationRow(index, 'dc_wiring_loss')).toBeUndefined();
  });

  it('tolerates null/empty rows', () => {
    expect(buildReconciliationIndex(null).size).toBe(0);
    expect(buildReconciliationIndex(undefined).size).toBe(0);
    expect(buildReconciliationIndex([]).size).toBe(0);
  });

  it('exposes every protected Overview field in the field map', () => {
    [
      'dc_wiring_loss',
      'ac_wiring_loss',
      'medium_voltage_loss',
      'mv_line_loss',
      'module_quantity',
      'inverter_quantity',
      'project_type',
      'permission_to_operate',
      'system_size_dc',
      'system_size_ac',
      'year_one_expected_production',
      'degradation_amount'
    ].forEach(field => {
      expect(OVERVIEW_FIELD_TO_RECON[field]?.length).toBeGreaterThan(0);
    });
  });
});

describe('reconciliationFieldMap — resolveProtectedValue precedence', () => {
  it('falls back to the card value when the user cannot view reconciliation', () => {
    const row = makeRow({ active_fact_value: 99 });
    const result = resolveProtectedValue(row, 1.5, false);
    expect(result).toEqual({ value: 1.5, source: 'fallback', qualifier: null });
  });

  it('falls back to the card value when no row is available', () => {
    const result = resolveProtectedValue(undefined, 1.5, true);
    expect(result).toEqual({ value: 1.5, source: 'fallback', qualifier: null });
  });

  it('prefers the active fact value (no qualifier)', () => {
    const row = makeRow({ active_fact_value: 2.5, accepted_value: 3, ai_extracted_value: 4, legacy_value: 5 });
    const result = resolveProtectedValue(row, 1.5, true);
    expect(result.value).toBe(2.5);
    expect(result.source).toBe('active_fact');
    expect(result.qualifier).toBeNull();
  });

  it('uses accepted value with the "not promoted" qualifier when no active fact', () => {
    const row = makeRow({ accepted_value: 3, ai_extracted_value: 4, legacy_value: 5 });
    const result = resolveProtectedValue(row, 1.5, true);
    expect(result.value).toBe(3);
    expect(result.source).toBe('accepted');
    expect(result.qualifier).toMatch(/not promoted/i);
  });

  it('uses ai-extracted value with the review qualifier next', () => {
    const row = makeRow({ ai_extracted_value: 4, legacy_value: 5 });
    const result = resolveProtectedValue(row, 1.5, true);
    expect(result.value).toBe(4);
    expect(result.source).toBe('ai_extracted');
    expect(result.qualifier).toMatch(/review/i);
  });

  it('uses legacy value with the display-only qualifier last', () => {
    const row = makeRow({ legacy_value: 5 });
    const result = resolveProtectedValue(row, 1.5, true);
    expect(result.value).toBe(5);
    expect(result.source).toBe('legacy');
    expect(result.qualifier).toMatch(/legacy/i);
  });

  it('falls back to the card value when the row carries no precedence values', () => {
    const row = makeRow({});
    const result = resolveProtectedValue(row, 1.5, true);
    expect(result).toEqual({ value: 1.5, source: 'fallback', qualifier: null });
  });

  it('treats 0 and false as present (not skipped)', () => {
    expect(resolveProtectedValue(makeRow({ active_fact_value: 0 }), 1.5, true)).toMatchObject({
      value: 0,
      source: 'active_fact'
    });
    expect(resolveProtectedValue(makeRow({ active_fact_value: false }), 1.5, true)).toMatchObject({
      value: false,
      source: 'active_fact'
    });
  });

  it('treats empty/whitespace strings as absent and continues down precedence', () => {
    const row = makeRow({ active_fact_value: '   ', accepted_value: 'X' });
    const result = resolveProtectedValue(row, 'fallback', true);
    expect(result.value).toBe('X');
    expect(result.source).toBe('accepted');
  });
});

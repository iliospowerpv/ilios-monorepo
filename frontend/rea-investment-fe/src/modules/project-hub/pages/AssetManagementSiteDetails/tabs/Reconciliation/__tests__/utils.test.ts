import { canPromoteRow, canCreateTaskRow, promotionErrorMessage } from '../utils';
import type { ReconciliationRow } from '../../../../../../../api';

const row = (overrides: Partial<ReconciliationRow>): ReconciliationRow =>
  ({
    canonical_field: 'module_capacity_kw',
    display_label: 'Module Capacity',
    category: 'baseline_physics',
    status: 'accepted_not_promoted',
    required_action: 'Promote this value',
    document_id: 5,
    document_version_id: 9,
    ...overrides
  }) as ReconciliationRow;

describe('canPromoteRow', () => {
  it('is true for an accepted-not-promoted row with both document ids', () => {
    expect(canPromoteRow(row({}))).toBe(true);
  });

  it('is false when the status is not accepted_not_promoted', () => {
    expect(canPromoteRow(row({ status: 'active_fact' }))).toBe(false);
    expect(canPromoteRow(row({ status: 'candidate_only' }))).toBe(false);
  });

  it('is false when document_id is missing', () => {
    expect(canPromoteRow(row({ document_id: null }))).toBe(false);
  });

  it('is false when document_version_id is missing', () => {
    expect(canPromoteRow(row({ document_version_id: null }))).toBe(false);
  });
});

describe('canCreateTaskRow', () => {
  it('is true when a required_action is present', () => {
    expect(canCreateTaskRow(row({ required_action: 'Accept in Data Room' }))).toBe(true);
  });

  it('is false when there is no required_action', () => {
    expect(canCreateTaskRow(row({ required_action: null }))).toBe(false);
  });
});

describe('promotionErrorMessage', () => {
  it('maps 403 to a permission message', () => {
    expect(promotionErrorMessage({ response: { status: 403 } })).toMatch(/permission/i);
  });

  it('maps a "File not found" 400 to a refresh message', () => {
    const msg = promotionErrorMessage({ response: { status: 400, data: { detail: 'File not found' } } });
    expect(msg).toMatch(/no longer valid/i);
  });

  it('maps a "does not belong" mismatch 400 to a refresh message', () => {
    const msg = promotionErrorMessage({
      response: { status: 400, data: { detail: 'File does not belong to document' } }
    });
    expect(msg).toMatch(/no longer valid/i);
  });

  it('maps a 404 to a refresh message', () => {
    expect(promotionErrorMessage({ response: { status: 404 } })).toMatch(/no longer valid/i);
  });

  it('surfaces the backend message for a 409 fail-closed freshness block', () => {
    const msg = promotionErrorMessage({
      response: {
        status: 409,
        data: {
          error_code: 'PROMOTION_SOURCE_STALE',
          message: 'Promotion blocked: 2 value(s) cannot be proven current. Re-review them in the Data Room.',
          stale_fields: [{ canonical_field: 'module_wattage', reason: 'source_run_outdated' }]
        }
      }
    });
    expect(msg).toMatch(/Promotion blocked/);
    expect(msg).toMatch(/Data Room/i);
  });

  it('falls back to a generic stale message when a 409 omits the backend message', () => {
    const msg = promotionErrorMessage({
      response: { status: 409, data: { error_code: 'PROMOTION_SOURCE_STALE' } }
    });
    expect(msg).toMatch(/Data Room/i);
  });

  it('maps any other failure to a nothing-changed message', () => {
    const msg = promotionErrorMessage({ response: { status: 400, data: { detail: 'Promotion failed: boom' } } });
    expect(msg).toMatch(/nothing was changed/i);
    expect(promotionErrorMessage({})).toMatch(/nothing was changed/i);
  });
});

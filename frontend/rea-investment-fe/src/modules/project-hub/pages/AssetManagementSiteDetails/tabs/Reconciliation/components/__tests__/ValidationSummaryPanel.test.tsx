import React from 'react';
import { render, screen } from '@testing-library/react';
import ValidationSummaryPanel from '../ValidationSummaryPanel';
import type { BaselinePhysicsValidation } from '../../../../../../../../types/telemetryV2';

const base: BaselinePhysicsValidation = {
  baseline_id: 1,
  is_blocking: false,
  summary: 'All inputs plausible.',
  policy_version: 'baseline-physics-v1'
};

describe('ValidationSummaryPanel', () => {
  it('renders an honest "not evaluated" neutral state for a null verdict', () => {
    render(<ValidationSummaryPanel validation={null} who="Proposed baseline" testIdPrefix="vs" />);
    expect(screen.getByTestId('vs-panel')).toBeInTheDocument();
    expect(screen.getByTestId('vs-unavailable')).toBeInTheDocument();
    expect(screen.getByTestId('vs-state-chip')).toHaveTextContent(/Not evaluated/i);
  });

  it('shows a summary-only note when the verdict carries no per-field detail', () => {
    render(
      <ValidationSummaryPanel
        validation={{ ...base, warning_field_count: 0 }}
        who="Active baseline"
        testIdPrefix="vs"
      />
    );
    expect(screen.getByTestId('vs-summary-only')).toBeInTheDocument();
    expect(screen.getByTestId('vs-state-chip')).toHaveTextContent(/Valid/i);
  });

  it('groups fields by severity and renders required_action guidance', () => {
    const v: BaselinePhysicsValidation = {
      ...base,
      is_blocking: true,
      blocking_field_count: 1,
      warning_field_count: 1,
      fields: [
        {
          field: 'module_wattage',
          entered_value: null,
          expected_unit: 'W',
          classification: 'hard_invalid',
          reason: 'Required physics field is absent.',
          source: 'facts_promotion',
          required_action: 'Promote a module wattage fact.'
        },
        {
          field: 'soiling_factor',
          entered_value: 0.7,
          expected_unit: 'ratio',
          classification: 'warning',
          reason: 'Unusually low.',
          source: 'facts_promotion',
          required_action: 'Confirm the soiling assumption.'
        },
        {
          field: 'dc_loss_pct',
          entered_value: 2,
          expected_unit: '%',
          classification: 'plausible',
          reason: 'ok',
          source: 'facts_promotion',
          required_action: null
        }
      ]
    };
    render(<ValidationSummaryPanel validation={v} who="Proposed baseline" testIdPrefix="vs" />);
    expect(screen.getByTestId('vs-blocking')).toBeInTheDocument();
    expect(screen.getByTestId('vs-warning')).toBeInTheDocument();
    expect(screen.getByTestId('vs-plausible')).toBeInTheDocument();
    expect(screen.getByTestId('vs-action-module_wattage')).toHaveTextContent('Promote a module wattage fact.');
    expect(screen.getByTestId('vs-action-soiling_factor')).toHaveTextContent('Confirm the soiling assumption.');
    expect(screen.getByTestId('vs-state-chip')).toHaveTextContent(/Blocked/i);
  });
});

import React from 'react';
import { render, screen } from '@testing-library/react';
import ActivationReadinessSummary from '../ActivationReadinessSummary';
import type { BaselinePhysicsValidation, ExpectedBaselineResponse } from '../../../../../../../../types/telemetryV2';

const makeBaseline = (over: Partial<ExpectedBaselineResponse> = {}): ExpectedBaselineResponse => ({
  id: 902,
  company_id: 1,
  site_id: 4,
  baseline_name: 'WA Baseline',
  baseline_type: 'weather_adjusted_model',
  status: 'approved',
  version: 4,
  ...over
});

describe('ActivationReadinessSummary', () => {
  it('renders an honest neutral note when no verdict is supplied', () => {
    render(<ActivationReadinessSummary baseline={makeBaseline()} priorActive={null} validation={null} />);
    expect(screen.getByTestId('activation-readiness-summary')).toBeInTheDocument();
    expect(screen.getByTestId('activation-readiness-summary-blocking-unknown')).toBeInTheDocument();
    // First-active case: no prior to supersede.
    expect(screen.getByTestId('activation-readiness-summary-supersedes')).toHaveTextContent(/first active/i);
  });

  it('warns about blocking values and missing PTO, and names the superseded baseline', () => {
    const validation: BaselinePhysicsValidation = {
      baseline_id: 902,
      is_blocking: true,
      summary: 'blocked',
      policy_version: 'v1',
      blocking_field_count: 2,
      warning_field_count: 0
    };
    render(
      <ActivationReadinessSummary
        baseline={makeBaseline({ pto_date: null })}
        priorActive={makeBaseline({ id: 800, baseline_name: 'Prior WA', status: 'active' })}
        validation={validation}
      />
    );
    expect(screen.getByTestId('activation-readiness-summary-blocking')).toHaveTextContent(/2/);
    expect(screen.getByTestId('activation-readiness-summary-pto')).toHaveTextContent(/No PTO date/i);
    expect(screen.getByTestId('activation-readiness-summary-supersedes')).toHaveTextContent(/Prior WA/);
    expect(screen.getByTestId('activation-readiness-summary-design-points')).toHaveTextContent(/separate track/i);
  });

  it('confirms readiness when there are no blocking values or warnings', () => {
    const validation: BaselinePhysicsValidation = {
      baseline_id: 902,
      is_blocking: false,
      summary: 'ok',
      policy_version: 'v1',
      blocking_field_count: 0,
      warning_field_count: 0
    };
    render(
      <ActivationReadinessSummary
        baseline={makeBaseline({ pto_date: '2025-01-01' })}
        priorActive={null}
        validation={validation}
      />
    );
    expect(screen.getByTestId('activation-readiness-summary-blocking')).toHaveTextContent(/No blocking values/i);
    expect(screen.getByTestId('activation-readiness-summary-warnings')).toHaveTextContent(/No warnings/i);
    expect(screen.getByTestId('activation-readiness-summary-pto')).toHaveTextContent(/PTO date set/i);
  });
});

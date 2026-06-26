import React from 'react';
import { render, screen } from '@testing-library/react';
import ValidationHistoryPanel from '../ValidationHistoryPanel';
import type { ExpectedBaselineResponse } from '../../../../../../../../types/telemetryV2';

const makeBaseline = (over: Partial<ExpectedBaselineResponse> = {}): ExpectedBaselineResponse => ({
  id: 1,
  company_id: 1,
  site_id: 4,
  baseline_name: 'WA Baseline',
  baseline_type: 'weather_adjusted_model',
  status: 'draft',
  version: 1,
  ...over
});

describe('ValidationHistoryPanel', () => {
  it('renders nothing when there are no baselines', () => {
    const { container } = render(<ValidationHistoryPanel baselines={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('lists every version newest-first with status and supersession', () => {
    render(
      <ValidationHistoryPanel
        baselines={[
          makeBaseline({ id: 800, version: 3, status: 'superseded', active_from: '2025-01-01T00:00:00' }),
          makeBaseline({
            id: 902,
            version: 4,
            status: 'active',
            supersedes_baseline_id: 800,
            active_from: '2025-06-01T00:00:00'
          })
        ]}
      />
    );
    expect(screen.getByTestId('validation-history-panel')).toBeInTheDocument();
    expect(screen.getByTestId('validation-history-panel-row-902')).toHaveTextContent(/Supersedes #800/);
    expect(screen.getByTestId('validation-history-panel-row-902')).toHaveTextContent(/Active/i);
    expect(screen.getByTestId('validation-history-panel-row-800')).toHaveTextContent(/Superseded/i);
  });
});

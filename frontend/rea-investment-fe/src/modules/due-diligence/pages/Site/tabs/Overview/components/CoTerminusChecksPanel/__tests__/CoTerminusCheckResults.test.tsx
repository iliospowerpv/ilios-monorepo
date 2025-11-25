import { screen, render } from '@testing-library/react';
import CoTerminusCheckResults from '../CoTerminusCheckResults';

jest.mock('../CoTerminusCheckSummary', () => ({
  __esModule: true,
  default: () => <div>CoTerminusCheckSummary-component-placeholder</div>
}));

jest.mock('../TermCheckResult', () => ({
  __esModule: true,
  default: () => <div>TermCheckResult-component-placeholder</div>
}));

describe('CoTerminusCheckResults component', () => {
  it('should render and function correctly', () => {
    const { rerender } = render(
      <CoTerminusCheckResults
        hasError={false}
        isLoadingResults={false}
        isCheckInProgress={false}
        summary={[]}
        results={[]}
      />
    );

    expect(screen.getByText('Nothing to show yet')).toBeInTheDocument();

    rerender(
      <CoTerminusCheckResults
        hasError={false}
        isLoadingResults={false}
        isCheckInProgress={false}
        summary={[
          {
            status: 'Equal',
            count: 5
          }
        ]}
        results={[
          {
            name: 'Renewal Terms',
            status: 'N/A',
            sources: { 'Site Lease': '15 years' }
          },
          {
            name: 'Effective Date',
            status: 'Equal',
            sources: { 'O&M Agreement': '10/07' }
          }
        ]}
      />
    );

    expect(screen.getByText('CoTerminusCheckSummary-component-placeholder')).toBeInTheDocument();
    expect(screen.getAllByText('TermCheckResult-component-placeholder').length).toBe(2);
  });
});

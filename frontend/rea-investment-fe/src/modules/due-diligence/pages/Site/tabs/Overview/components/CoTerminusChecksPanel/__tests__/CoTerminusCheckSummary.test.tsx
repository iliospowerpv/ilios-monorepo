import { render, screen, within } from '@testing-library/react';
import CoTerminusCheckSummary from '../CoTerminusCheckSummary';

describe('CoTerminusCheckSummary component', () => {
  const summaryMock = [
    {
      status: 'Equal',
      count: 5
    },
    {
      status: 'Ambiguous',
      count: 12
    },
    {
      status: 'N/A',
      count: 3
    }
  ];

  test('should render and function correctly', () => {
    render(<CoTerminusCheckSummary summaryItems={summaryMock} />);

    const equalEntry = screen.getByTestId('co-terminus-summary-Equal-entry');
    expect(within(equalEntry).getByText('5')).toBeInTheDocument();
    const notEqualEntry = screen.getByTestId('co-terminus-summary-Not Equal-entry');
    expect(within(notEqualEntry).getByText('0')).toBeInTheDocument();
  });
});

import { screen, render } from '@testing-library/react';
import TermCheckResult from '../TermCheckResult';

describe('TermCheckResult', () => {
  it('should render and function correctly', () => {
    render(<TermCheckResult name="Renewal Terms" status="N/A" sources={{ 'Site Lease': '15 years' }} />);

    expect(screen.getByText('Renewal Terms')).toBeInTheDocument();
    expect(screen.getByText('Site Lease')).toBeInTheDocument();
    expect(screen.getByText('15 years')).toBeInTheDocument();
    expect(screen.getByTestId('HelpIcon')).toBeInTheDocument();
  });
});

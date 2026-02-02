import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { OwnershipCard } from '../Ownership';

jest.mock('../../../../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn()
}));

describe('OwnershipCard form component', () => {
  const queryClient = new QueryClient();

  it('renders and functions correctly', async () => {
    const data = {
      ownership_structure: 'Tax Equity Only',
      hold_co: 'Shawmut Solar Holdings, LLC',
      project_co: '',
      guarantor: '',
      tax_credit_fund: ''
    };

    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <OwnershipCard siteId={5} data={data} />
        </QueryClientProvider>
      </BrowserRouter>
    );

    const editBtn = screen.getByTestId('ownership-edit-btn');

    fireEvent.click(editBtn);

    await waitFor(() => {
      expect(screen.getAllByRole('textbox').length).toBe(3);
    });
  });
});

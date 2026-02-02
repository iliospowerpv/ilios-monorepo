import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { InsuranceProviderCard } from '../InsuranceProvider';

jest.mock('../../../../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn()
}));

describe('InsuranceProvider Card form component', () => {
  const queryClient = new QueryClient();

  it('renders and functions correctly', async () => {
    const data = {
      insurance_provider: 'Wellp',
      insurance_address: '1500 19th Ave. SW Byron, MN 55920'
    };

    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <InsuranceProviderCard siteId={5} data={data} />
        </QueryClientProvider>
      </BrowserRouter>
    );

    const editBtn = screen.getByTestId('insurance_provider-edit-btn');

    fireEvent.click(editBtn);

    await waitFor(() => {
      expect(screen.getAllByRole('textbox').length).toBe(2);
    });
  });
});

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { OMCard } from '../OM';

jest.mock('../../../../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn()
}));

describe('SiteLeaseCard form component', () => {
  const queryClient = new QueryClient();

  it('renders and functions correctly', async () => {
    const data = {
      provider: 'Wellp',
      agreement_effective_date: '-',
      o_and_m_rate: '-',
      o_and_m_escalator: '-',
      production_guarantee: '-',
      contact: '1500 19th Ave. SW Byron, MN 55920',
      contact_name: 'John Starks',
      contact_email: 'johnstarks@gmail.com',
      contact_phone: '5733455671'
    };

    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <OMCard siteId={5} data={data} />
        </QueryClientProvider>
      </BrowserRouter>
    );

    const editBtn = screen.getByTestId('o&m-edit-btn');

    fireEvent.click(editBtn);

    await waitFor(() => {
      expect(screen.getAllByRole('textbox').length).toBe(4);
    });
  });
});

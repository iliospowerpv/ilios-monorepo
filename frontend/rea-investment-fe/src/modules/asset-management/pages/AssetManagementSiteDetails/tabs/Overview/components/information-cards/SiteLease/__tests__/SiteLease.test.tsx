import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { SiteLeaseCard } from '../SiteLease';

jest.mock('../../../../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn()
}));

describe('SiteLeaseCard form component', () => {
  const queryClient = new QueryClient();

  it('renders and functions correctly', async () => {
    const data = {
      landlord: 'Brixmor Holdings 1 SPE, LLC',
      tenant: 'GreenLife Solar, LLC d/b/a Shine Development Partners',
      property_size: '24.6257',
      effective_date: '01/07/25',
      rent_commencement: '01/07/24',
      rent_amount: '24625.7',
      rent_escalator: '2',
      rent_escalator_effective_date: '01/07/26',
      payment_due_date: '25 years from COD',
      lease_payment_method: 'Check',
      lease_payment_frequency: 'Monthly',
      initial_term: '20 years beginning on the date the Permission to Operate was issued',
      renewal_terms:
        'Three (3) additional five (5) year periods with written notice ninety (90) days prior to the expiration',
      landlord_contact_phone: '6045685678'
    };

    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <SiteLeaseCard siteId={5} data={data} />
        </QueryClientProvider>
      </BrowserRouter>
    );

    const editBtn = screen.getByTestId('site_lease-edit-btn');

    fireEvent.click(editBtn);

    await waitFor(() => {
      expect(screen.getAllByRole('textbox').length).toBe(5);
    });
  });
});

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { InterconnectionUtilityProviderCard } from '../InterconnectionUtilityProvider';

jest.mock('../../../../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn()
}));

describe('InterconnectionUtilityProviderCard form component', () => {
  const queryClient = new QueryClient();

  it('renders and functions correctly', async () => {
    const data = {
      iut_address: '60 Campanelli Drive, Braintree, MA',
      iut_contact_name: 'Stan Mcbride',
      iut_contact_email: 'stanmcbride@gmail.com',
      iut_contact_phone: '6043455671',
      utility_rate: 'none',
      provider: null,
      ppa_term: 'Gram',
      ppa_effective_date: '1963',
      production_guarantee: null,
      interconnection_agreement_effective_date: '1963',
      remaining_ppa_term: null
    };

    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <InterconnectionUtilityProviderCard siteId={5} data={data} />
        </QueryClientProvider>
      </BrowserRouter>
    );

    const editBtn = screen.getByTestId('interconnection_utility_provider-edit-btn');

    fireEvent.click(editBtn);

    await waitFor(() => {
      expect(screen.getAllByRole('textbox').length).toBe(5);
    });
  });
});

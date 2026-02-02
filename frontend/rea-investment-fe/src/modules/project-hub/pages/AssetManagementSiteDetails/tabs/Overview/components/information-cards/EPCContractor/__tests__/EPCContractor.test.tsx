import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { EPCContractorCard } from '../EPCContractor';

jest.mock('../../../../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn()
}));

describe('SiteLeaseCard form component', () => {
  const queryClient = new QueryClient();

  it('renders and functions correctly', async () => {
    const data = {
      provider: 'SunRaise Development, LLC',
      agreement_effective_date: '01/07/22',
      contact: '1503 Country Club Rd SE, Byron, MN 55920',
      contact_name: 'Collin Drake',
      contact_email: 'collindr@gmail.com',
      contact_phone: '6043455671'
    };

    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <EPCContractorCard siteId={5} data={data} />
        </QueryClientProvider>
      </BrowserRouter>
    );

    const editBtn = screen.getByTestId('epc_contractor-edit-btn');

    fireEvent.click(editBtn);

    await waitFor(() => {
      expect(screen.getAllByRole('textbox').length).toBe(4);
    });
  });
});

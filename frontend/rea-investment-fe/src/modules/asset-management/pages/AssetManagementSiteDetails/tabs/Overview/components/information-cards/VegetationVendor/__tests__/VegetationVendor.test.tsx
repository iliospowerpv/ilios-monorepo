import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { VegetationVendorCard } from '../VegetationVendor';

jest.mock('../../../../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn()
}));

describe('VegetationVendorCard form component', () => {
  const queryClient = new QueryClient();

  it('renders and functions correctly', async () => {
    const data = {
      vv_provider: 'Acme Corporation',
      vv_address: '5445 N 27th St, Milwaukee, WI',
      vv_contact_name: 'John Doe',
      vv_contact_phone: '5551234567',
      vv_contact__email: 'john.doe@acmecorp.com'
    };

    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <VegetationVendorCard siteId={5} data={data} />
        </QueryClientProvider>
      </BrowserRouter>
    );

    const editBtn = screen.getByTestId('vegetation_vendor-edit-btn');

    fireEvent.click(editBtn);

    await waitFor(() => {
      expect(screen.getAllByRole('textbox').length).toBe(5);
    });
  });
});

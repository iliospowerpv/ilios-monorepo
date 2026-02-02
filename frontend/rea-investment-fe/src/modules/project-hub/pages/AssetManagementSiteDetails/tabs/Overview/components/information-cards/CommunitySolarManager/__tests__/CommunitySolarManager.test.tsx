import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { CommunitySolarManagerCard } from '../CommunitySolarManager';

jest.mock('../../../../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn()
}));

describe('Community Solar Manager form component', () => {
  const queryClient = new QueryClient();

  it('renders and functions correctly', async () => {
    const data = {
      csm_provider: 'text',
      csm_address: 'text address',
      csm_contact_name: 'Kevin',
      csm_contact_email: 'test@gmail.com',
      csm_contact_phone: '777-7777-777',
      csm_fee: 5,
      escalator: 3,
      escalator_effective: '11/11/11'
    };

    render(
      <BrowserRouter>
        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <QueryClientProvider client={queryClient}>
            <CommunitySolarManagerCard siteId={5} data={data} />
          </QueryClientProvider>
        </LocalizationProvider>
      </BrowserRouter>
    );

    const editBtn = screen.getByTestId('community_solar_manager-edit-btn');

    fireEvent.click(editBtn);

    await waitFor(() => {
      expect(screen.getAllByRole('textbox').length).toBe(8);
    });
  });
});

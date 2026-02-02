import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { SiteLevelDetailsCard } from '../SiteLevelDetails';

jest.mock('../../../../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn()
}));

describe('Community Solar Manager form component', () => {
  const queryClient = new QueryClient();

  it('renders and functions correctly', async () => {
    const data = {
      status: 'status',
      project_id: '5',
      pvsyst: 'https://www.google.com',
      greenhouse_gas_offset: 'test',
      incentive_program: 'test',
      das_provider: 'test',
      das_account: 'test',
      das_username: 'test',
      das_password: 'test',
      name: 'test',
      address: 'test',
      city: 'test',
      state: 'test',
      zip_code: 'test',
      system_size_ac: 5,
      system_size_dc: 10,
      lon_lat_url: 'test',
      year_one_expected_production: 'test',
      degradation_amount: '4'
    };

    render(
      <BrowserRouter>
        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <QueryClientProvider client={queryClient}>
            <SiteLevelDetailsCard siteId={5} data={data} />
          </QueryClientProvider>
        </LocalizationProvider>
      </BrowserRouter>
    );

    const editBtn = screen.getByTestId('site_level_details-edit-btn');

    fireEvent.click(editBtn);

    await waitFor(() => {
      expect(screen.getAllByRole('textbox').length).toBe(8);
    });
  });
});

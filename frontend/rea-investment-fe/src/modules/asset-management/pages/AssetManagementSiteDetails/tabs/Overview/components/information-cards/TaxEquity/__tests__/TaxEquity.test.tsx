import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { TaxEquityCard } from '../TaxEquity';
import { LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';

jest.mock('../../../../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn()
}));

describe('Tax Equity Card form component', () => {
  const queryClient = new QueryClient();

  it('renders and functions correctly', async () => {
    const data = {
      tax_equity_fund: 'test',
      tax_equity_provider: 'test1',
      tax_equity_buyout_amount: 5,
      tax_equity_buyout_date: '11/11/11',
      tax_equity_pref_rate: 15.3,
      smartsheet_data_tape: 'test3'
    };

    render(
      <BrowserRouter>
        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <QueryClientProvider client={queryClient}>
            <TaxEquityCard siteId={5} data={data} />
          </QueryClientProvider>
        </LocalizationProvider>
      </BrowserRouter>
    );

    const editBtn = screen.getByTestId('tax_equity-edit-btn');

    fireEvent.click(editBtn);

    await waitFor(() => {
      expect(screen.getAllByRole('textbox').length).toBe(6);
    });
  });
});

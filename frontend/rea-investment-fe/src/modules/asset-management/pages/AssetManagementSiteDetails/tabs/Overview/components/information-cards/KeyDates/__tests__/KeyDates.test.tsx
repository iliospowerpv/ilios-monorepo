import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { KeyDatesCard } from '../KeyDates';

jest.mock('../../../../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn()
}));

describe('KeyDatesCard form component', () => {
  const queryClient = new QueryClient();

  it('renders and functions correctly', async () => {
    const data = {
      mechanical_completion_date: null,
      substantial_completion_date: null,
      final_completion_date: null,
      permission_to_operate: '2025-01-07',
      placed_in_service_date: '2020-04-01',
      financial_close_date: '2025-07-01'
    };

    render(
      <BrowserRouter>
        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <QueryClientProvider client={queryClient}>
            <KeyDatesCard siteId={5} data={data} />
          </QueryClientProvider>
        </LocalizationProvider>
      </BrowserRouter>
    );

    const editBtn = screen.getByTestId('key_dates-edit-btn');

    fireEvent.click(editBtn);

    await waitFor(() => {
      expect(screen.getAllByRole('textbox').length).toBe(3);
    });
  });
});

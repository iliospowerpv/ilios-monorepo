import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { KeyDatesCard } from '../KeyDates';

jest.mock('../../../../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn()
}));

jest.mock('../../../../../../../../../../contexts/auth/auth', () => ({
  useAuth: () => ({ user: { is_system_user: true } })
}));

describe('KeyDatesCard form component', () => {
  const queryClient = new QueryClient();

  const data = {
    mechanical_completion_date: null,
    substantial_completion_date: null,
    final_completion_date: null,
    permission_to_operate: '2025-01-07',
    placed_in_service_date: '2020-04-01',
    financial_close_date: '2025-07-01'
  };

  const renderCard = () =>
    render(
      <BrowserRouter>
        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <QueryClientProvider client={queryClient}>
            <KeyDatesCard siteId={5} data={data} />
          </QueryClientProvider>
        </LocalizationProvider>
      </BrowserRouter>
    );

  it('renders Permission to Operate read-only with a provenance label and a Data Room link', () => {
    renderCard();

    // Only PTO is baseline-driving / read-only in this card.
    expect(screen.getAllByText(/Baseline-driving/i).length).toBe(1);
    expect(screen.getByRole('link', { name: /open data room/i })).toBeTruthy();
  });

  it('keeps the other two dates editable while PTO stays read-only in edit mode', async () => {
    renderCard();

    fireEvent.click(screen.getByTestId('key_dates-edit-btn'));

    // Placed in Service and Financial Close remain editable date inputs; PTO does not.
    await waitFor(() => {
      expect(screen.getAllByRole('textbox').length).toBe(2);
    });
    expect(screen.getAllByText(/Baseline-driving/i).length).toBe(1);
  });
});

import { screen, render, act, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';

import { useNotify } from '../../../../../../../../../contexts/notifications/notifications';
import ServiceDetailCard from '../ServiceDetailCard';

import deviceDetailsResponseStub from './deviceDetailsDataResponseStub.json';

jest.mock('../../../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn()
}));

describe('ServiceDetailCard component', () => {
  it('should render and function correctly', async () => {
    const queryClient = new QueryClient();

    if (jest.isMockFunction(useNotify)) {
      useNotify.mockReturnValue(jest.fn());
    }

    await act(() =>
      render(
        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <QueryClientProvider client={queryClient}>
            <ServiceDetailCard
              siteId={4}
              deviceId={12}
              serviceDetailData={deviceDetailsResponseStub.service_detail as any}
            />
          </QueryClientProvider>
        </LocalizationProvider>
      )
    );

    await waitFor(() => {
      expect(screen.getByText('Service Details')).toBeInTheDocument();
    });

    const editBtn = screen.getByRole('button');
    fireEvent.click(editBtn);

    await waitFor(() => {
      expect(screen.getAllByRole('textbox').length).toBe(2);
    });
  });
});

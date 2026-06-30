import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import Settings from '../Settings';

const queryClient = new QueryClient();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: jest.fn(() => jest.fn())
}));

jest.mock('../../../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn(() => jest.fn())
}));

describe('Settings page', () => {
  const renderSettings = () =>
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <Settings />
        </QueryClientProvider>
      </BrowserRouter>
    );

  test('renders without crashing', () => {
    renderSettings();

    expect(screen.getByText(/Settings/i)).toBeInTheDocument();
  });

  test('does not render the dead Notification and Alerts tabs', () => {
    renderSettings();

    expect(screen.queryByTestId('tab__notification')).not.toBeInTheDocument();
    expect(screen.queryByTestId('tab__alerts')).not.toBeInTheDocument();
  });

  test('defaults to the Audit Logs tab', () => {
    renderSettings();

    expect(screen.getByTestId('tab__audit-logs')).toHaveAttribute('aria-selected', 'true');
  });
});

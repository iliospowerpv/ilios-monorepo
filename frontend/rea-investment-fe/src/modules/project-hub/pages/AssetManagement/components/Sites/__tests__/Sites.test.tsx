import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Sites from '../Sites';
import { AuthProvider } from '../../../../../../../contexts/auth/auth';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

describe('Asset Management page - Sites tab', () => {
  const queryClient = new QueryClient();

  test('renders the page', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <Sites />
          </AuthProvider>
        </QueryClientProvider>
      </BrowserRouter>
    );

    expect(screen.getByTestId('grid__base-table')).toBeInTheDocument();
    expect(screen.getByTestId('actions__container')).toBeInTheDocument();
  });

  test('has correct column headers', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <Sites />
          </AuthProvider>
        </QueryClientProvider>
      </BrowserRouter>
    );

    expect(screen.getByText('Site Name')).toBeInTheDocument();
    expect(screen.getByText('Company Name')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('Address')).toBeInTheDocument();
    expect(screen.getByText('City')).toBeInTheDocument();
    expect(screen.getByText('State')).toBeInTheDocument();
  });
});

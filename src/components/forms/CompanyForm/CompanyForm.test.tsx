import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { CompanyForm } from './CompanyForm';
import { NotificationsProvider } from '../../../contexts/notifications/notifications';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

describe('Company form component', () => {
  const queryClient = new QueryClient();

  test('renders the form', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <NotificationsProvider>
            <CompanyForm mode="add" />
          </NotificationsProvider>
        </QueryClientProvider>
      </BrowserRouter>
    );

    expect(screen.getByTestId('company__form')).toBeInTheDocument();
  });
});

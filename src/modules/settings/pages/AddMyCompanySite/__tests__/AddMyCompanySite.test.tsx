import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { NotificationsProvider } from '../../../../../contexts/notifications/notifications';
import AddMyCompanySite from '../AddMyCompanySite';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

describe('Add site page', () => {
  const queryClient = new QueryClient();

  test('renders the form', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <NotificationsProvider>
            <AddMyCompanySite />
          </NotificationsProvider>
        </QueryClientProvider>
      </BrowserRouter>
    );

    expect(screen.getByTestId('add-site__form-title')).toBeInTheDocument();
  });
});

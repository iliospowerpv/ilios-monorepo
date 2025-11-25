import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { ConnectionForm } from '../ConnectionForm';
import { NotificationsProvider } from '../../../../contexts/notifications/notifications';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

describe('Connection form component', () => {
  const queryClient = new QueryClient();

  test('renders the form', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <NotificationsProvider>
            <ConnectionForm
              companyId={1}
              connection={{ name: 'test', provider: 'Sunny Portal', token: '0123456789' }}
              onCancel={() => {}}
              onSave={() => {}}
            />
          </NotificationsProvider>
        </QueryClientProvider>
      </BrowserRouter>
    );

    expect(screen.getByTestId('connection__form')).toBeInTheDocument();
  });
});

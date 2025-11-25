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
  test('renders without crashing', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <Settings />
        </QueryClientProvider>
      </BrowserRouter>
    );

    expect(screen.getByText(/Settings/i)).toBeInTheDocument();
  });
});

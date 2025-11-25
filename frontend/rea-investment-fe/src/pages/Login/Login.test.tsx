import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import Login from './Login';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

describe('Login page', () => {
  const queryClient = new QueryClient();

  test('renders the form', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <Login />
        </QueryClientProvider>
      </BrowserRouter>
    );

    expect(screen.getByTestId('login__signin-form-title')).toBeInTheDocument();
  });
});

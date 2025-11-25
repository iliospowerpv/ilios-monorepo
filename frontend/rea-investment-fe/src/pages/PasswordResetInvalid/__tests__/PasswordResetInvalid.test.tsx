import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import PasswordResetInvalid from '../PasswordResetInvalid';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

describe('Password Reset Invalid page', () => {
  const queryClient = new QueryClient();

  test('renders the page', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <PasswordResetInvalid />
        </QueryClientProvider>
      </BrowserRouter>
    );

    expect(screen.getByTestId('reset__password-reset-invalid-title')).toBeInTheDocument();
  });
});

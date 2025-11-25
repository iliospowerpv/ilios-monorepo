import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import Companies from '../Companies';

const queryClient = new QueryClient();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: jest.fn(() => jest.fn())
}));

describe('CompaniesTab page', () => {
  test('renders without crashing', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <Companies />
      </QueryClientProvider>
    );

    expect(screen.getByTestId('grid__base-table')).toBeInTheDocument();
  });
});

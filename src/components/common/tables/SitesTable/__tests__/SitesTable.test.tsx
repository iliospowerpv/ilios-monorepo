import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import SitesTable from '../SitesTable';
import { AuthProvider } from '../../../../../contexts/auth/auth';

const columns = [
  {
    headerName: 'Site Name',
    field: 'name',
    flex: 1,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'Company Name',
    field: 'company.name',
    colId: 'company_name',
    flex: 1,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'Address',
    field: 'address',
    flex: 1,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'City',
    field: 'city',
    flex: 1,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'Status',
    field: 'status',
    flex: 1,
    checked: true,
    isDefault: true
  }
];

describe('SitesTable', () => {
  const queryClient = new QueryClient();

  test('renders the table', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <SitesTable columns={columns} />
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
            <SitesTable columns={columns} />
          </AuthProvider>
        </QueryClientProvider>
      </BrowserRouter>
    );

    expect(screen.getByText('Site Name')).toBeInTheDocument();
    expect(screen.getByText('Company Name')).toBeInTheDocument();
    expect(screen.getByText('Address')).toBeInTheDocument();
    expect(screen.getByText('City')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
  });
});

import React from 'react';
import { render, screen } from '@testing-library/react';
import { ColDef } from 'ag-grid-community';

import BaseTable from '../BaseTable';

const colDefs: ColDef[] = [{ field: 'name' }, { field: 'email' }, { field: 'role' }];
const rowData: any[] = [
  {
    id: 1,
    name: 'Jane Cooper',
    role: 'Due diligence manager',
    email: 'jane.cooper@example.com'
  },
  {
    id: 2,
    name: 'Tanya Hill',
    role: 'Financial manager',
    email: 'tanya.hill@example.com'
  }
];

describe('BasicTable', () => {
  test('renders the table', () => {
    render(<BaseTable columnDefs={colDefs} rowData={rowData} />);

    expect(screen.getByTestId('grid__base-table')).toBeInTheDocument();
  });

  test('has correct column headers', () => {
    render(<BaseTable columnDefs={colDefs} rowData={rowData} />);

    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Role')).toBeInTheDocument();
    expect(screen.getByText('Email')).toBeInTheDocument();
  });

  test('renders the correct number of rows', () => {
    const { container } = render(<BaseTable columnDefs={colDefs} rowData={rowData} />);

    const rows = container.querySelectorAll('.ag-row');
    const expectedRowsCount = 2;

    expect(rows.length).toBe(expectedRowsCount);
  });
});

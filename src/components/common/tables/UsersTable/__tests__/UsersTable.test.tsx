import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter as Router } from 'react-router-dom';

import UsersTable from '../UsersTable';

describe('UsersTable', () => {
  test('renders the table', () => {
    render(
      <Router>
        <UsersTable />
      </Router>
    );

    expect(screen.getByTestId('grid__base-table')).toBeInTheDocument();
    expect(screen.getByTestId('actions__container')).toBeInTheDocument();
  });

  test('has correct column headers', () => {
    render(
      <Router>
        <UsersTable />
      </Router>
    );

    expect(screen.getByText('First Name')).toBeInTheDocument();
    expect(screen.getByText('Last Name')).toBeInTheDocument();
    expect(screen.getByText('Email')).toBeInTheDocument();
    expect(screen.getByText('Role Name')).toBeInTheDocument();
    expect(screen.getByText('Actions')).toBeInTheDocument();
  });
});

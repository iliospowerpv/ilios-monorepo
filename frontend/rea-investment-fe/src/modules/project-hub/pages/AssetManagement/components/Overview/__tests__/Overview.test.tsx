import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Overview from '../Overview';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

describe('Asset Management page - Overview tab', () => {
  test('renders the page', () => {
    render(
      <BrowserRouter>
        <Overview />
      </BrowserRouter>
    );

    expect(screen.getByTestId('grid__base-table')).toBeInTheDocument();
  });

  test('has correct column headers', () => {
    render(
      <BrowserRouter>
        <Overview />
      </BrowserRouter>
    );

    expect(screen.getByText('Company Name')).toBeInTheDocument();
    expect(screen.getByText('Number of Sites')).toBeInTheDocument();
    expect(screen.getByText('System Size (kW)')).toBeInTheDocument();
  });
});

import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Companies from '../Companies';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

describe('Diligence page - Companies tab', () => {
  test('renders the page', () => {
    render(
      <BrowserRouter>
        <Companies />
      </BrowserRouter>
    );

    expect(screen.getByTestId('grid__base-table')).toBeInTheDocument();
  });

  test('has correct column headers', () => {
    render(
      <BrowserRouter>
        <Companies />
      </BrowserRouter>
    );

    expect(screen.getByText('Company Name')).toBeInTheDocument();
    expect(screen.getByText('Number of Sites')).toBeInTheDocument();
  });
});

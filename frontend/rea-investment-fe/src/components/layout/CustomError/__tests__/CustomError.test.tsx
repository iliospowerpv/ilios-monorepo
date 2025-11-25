import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter, useRouteError } from 'react-router-dom';

import CustomError from '../CustomError';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useRouteError: jest.fn()
}));

describe('CustomError', () => {
  test('renders the component', () => {
    (useRouteError as jest.Mock).mockReturnValue({ message: 'Test error' });

    render(
      <BrowserRouter>
        <CustomError />
      </BrowserRouter>
    );

    expect(screen.getByTestId('custom-error__component')).toBeInTheDocument();
    expect(screen.getByText('Something Went Wrong')).toBeInTheDocument();
  });
});

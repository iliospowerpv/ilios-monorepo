import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

import Error404 from '../Error404';

describe('Error404', () => {
  test('renders the component', () => {
    render(
      <BrowserRouter>
        <Error404 />
      </BrowserRouter>
    );

    expect(screen.getByTestId('error-404__component')).toBeInTheDocument();
  });
});

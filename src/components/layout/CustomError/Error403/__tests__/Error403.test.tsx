import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

import Error403 from '../Error403';

describe('Error403', () => {
  test('renders the component', () => {
    render(
      <BrowserRouter>
        <Error403 />
      </BrowserRouter>
    );

    expect(screen.getByTestId('error-403__component')).toBeInTheDocument();
  });
});

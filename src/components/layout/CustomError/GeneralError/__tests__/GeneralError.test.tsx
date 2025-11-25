import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

import GeneralError from '../GeneralError';

describe('GeneralError', () => {
  test('renders the component', () => {
    render(
      <BrowserRouter>
        <GeneralError message="Ooops!" />
      </BrowserRouter>
    );

    expect(screen.getByTestId('general-error__component')).toBeInTheDocument();
  });
});

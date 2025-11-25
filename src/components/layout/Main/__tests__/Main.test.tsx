import React from 'react';
import { render, screen } from '@testing-library/react';

import { Main } from '../Main';

describe('Main', () => {
  test('renders the component', () => {
    render(<Main />);

    expect(screen.getByTestId('main__component')).toBeInTheDocument();
  });
});

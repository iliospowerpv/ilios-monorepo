import React from 'react';
import { render, screen } from '@testing-library/react';

import { Copyright } from '../Copyright';

describe('Copyright', () => {
  test('renders the component', () => {
    render(<Copyright />);

    expect(screen.getByTestId('copyright__component')).toBeInTheDocument();
  });
});

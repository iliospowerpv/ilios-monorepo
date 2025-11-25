import React from 'react';
import { render, screen } from '@testing-library/react';

import { Logo } from '../Logo';

describe('Logo', () => {
  test('renders the component', () => {
    render(<Logo />);

    expect(screen.getByTestId('logo__component')).toBeInTheDocument();
  });
});

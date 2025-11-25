import React from 'react';
import { render, screen } from '@testing-library/react';

import { Header } from '../Header';

describe('Header', () => {
  test('renders the component', () => {
    render(<Header />);

    expect(screen.getByTestId('header__component')).toBeInTheDocument();
  });
});

import React from 'react';
import { render, screen } from '@testing-library/react';

import LoadingComponent from '../LoadingComponent';

describe('LoadingComponent', () => {
  test('renders the component', () => {
    render(<LoadingComponent />);

    expect(screen.getByTestId('loading__component')).toBeInTheDocument();
  });
});

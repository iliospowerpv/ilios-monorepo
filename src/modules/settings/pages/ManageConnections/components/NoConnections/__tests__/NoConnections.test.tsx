import React from 'react';
import { render, screen } from '@testing-library/react';

import NoConnections from '../NoConnections';

describe('NoConnections', () => {
  test('renders the component', () => {
    render(<NoConnections />);

    expect(screen.getByTestId('no-connections__component')).toBeInTheDocument();
  });
});

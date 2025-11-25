import React from 'react';
import { render, screen } from '@testing-library/react';

import ToggleGroup from './ToggleGroup';

describe('ToggleGroup page', () => {
  test('renders without crashing', () => {
    const mockFunction = jest.fn();

    render(<ToggleGroup alignment="list" setAlignment={mockFunction} />);

    expect(screen.getByTestId('toggle__group')).toBeInTheDocument();
  });
});

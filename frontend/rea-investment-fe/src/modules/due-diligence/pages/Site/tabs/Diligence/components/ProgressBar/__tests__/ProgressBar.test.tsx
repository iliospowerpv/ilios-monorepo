import React from 'react';
import { render, screen } from '@testing-library/react';
import ProgressBar from '../ProgressBar';

describe('ProgressBar component', () => {
  test('renders the component', () => {
    render(<ProgressBar value={99} />);

    expect(screen.getByTestId('progress-bar__component')).toBeInTheDocument();
  });
});

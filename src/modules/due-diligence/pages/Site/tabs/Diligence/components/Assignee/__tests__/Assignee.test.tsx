import React from 'react';
import { render, screen } from '@testing-library/react';
import Assignee from '../Assignee';

describe('Assignee component', () => {
  test('renders the component', () => {
    render(<Assignee user={null} />);

    expect(screen.getByTestId('assignee__component')).toBeInTheDocument();
  });
});

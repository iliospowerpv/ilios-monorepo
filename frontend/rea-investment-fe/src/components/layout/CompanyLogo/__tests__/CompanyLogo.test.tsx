import React from 'react';
import { render, screen } from '@testing-library/react';

import { CompanyLogo } from '../CompanyLogo';

describe('CompanyLogo', () => {
  test('renders the component', () => {
    render(<CompanyLogo />);

    expect(screen.getByTestId('company-logo__component')).toBeInTheDocument();
  });
});

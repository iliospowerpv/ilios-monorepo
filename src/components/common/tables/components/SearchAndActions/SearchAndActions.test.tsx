import React from 'react';
import { render, screen } from '@testing-library/react';

import SearchAndActions from './SearchAndActions';

describe('SearchAndActions', () => {
  test('renders the table', () => {
    render(<SearchAndActions showSearch={true} />);

    expect(screen.getByTestId('actions__search-field')).toBeInTheDocument();
  });

  test('has correct actions', () => {
    render(
      <SearchAndActions
        showSearch={true}
        showExport={true}
        showAdd={true}
        searchPlaceholder="Search by name and email"
      />
    );

    expect(screen.getByTestId('actions__search-field')).toBeInTheDocument();
    expect(screen.getByTestId('actions__export-btn')).toBeInTheDocument();
    expect(screen.getByTestId('actions__add-btn')).toBeInTheDocument();
  });
});

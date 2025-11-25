import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import AssetManagement from '../AssetManagement';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

describe('Asset Management page', () => {
  test('renders the page', () => {
    render(
      <BrowserRouter>
        <AssetManagement />
      </BrowserRouter>
    );

    expect(screen.getByTestId('asset-management__title')).toBeInTheDocument();
  });
});

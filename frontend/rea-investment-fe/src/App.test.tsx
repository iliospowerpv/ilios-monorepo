import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

jest.mock('./components/layout/BaseLayout/BaseLayout', () => ({
  BaseLayout: ({ children }: { children: React.ReactNode }) => (
    <div>
      <p>Breadcrumbs</p>
      {children}
    </div>
  )
}));

describe('App component', () => {
  test('renders without crashing', () => {
    render(<App />);

    expect(screen.getByText(/Breadcrumbs/i)).toBeInTheDocument();
  });
});

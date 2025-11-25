import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import '@testing-library/jest-dom';
import DueDiligencePage from './DueDiligence';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

describe('DueDiligence', () => {
  it('renders the DueDiligence heading', () => {
    render(
      <BrowserRouter>
        <DueDiligencePage />
      </BrowserRouter>
    );
    const heading = screen.getByText('Companies');
    expect(heading).toBeInTheDocument();
  });
});

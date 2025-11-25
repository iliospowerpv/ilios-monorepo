import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import DocumentItem from '../DocumentItem';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

const mockedDocument = {
  id: 448739,
  name: 'Executive Summary',
  files_count: 0,
  status: 'Undefined',
  assignee: null
};

describe('DocumentItem component', () => {
  test('renders the component', () => {
    render(
      <BrowserRouter>
        <DocumentItem document={mockedDocument} />
      </BrowserRouter>
    );

    expect(screen.getByTestId('document-item__component')).toBeInTheDocument();
  });
});

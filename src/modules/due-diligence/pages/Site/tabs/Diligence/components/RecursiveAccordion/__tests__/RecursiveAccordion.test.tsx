import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import RecursiveAccordion from '../RecursiveAccordion';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

const diligenceDocumentsMock = [
  {
    name: 'Executive Summary',
    documents_count: 1,
    documents: [
      {
        id: 1,
        name: 'Executive Summary',
        files_count: 22,
        status: 'Reviewing final notes',
        assignee: null
      }
    ],
    related_sections: [],
    completed_tasks_percentage: 15.01
  },
  {
    name: 'Preview',
    documents_count: 3,
    documents: [
      {
        id: 5,
        name: 'EPC Agreement',
        files_count: 3,
        status: 'In Progress',
        assignee: {
          id: 1,
          first_name: 'John',
          last_name: 'Doe'
        }
      },
      {
        id: 4,
        name: 'O&M Agreement',
        files_count: 0,
        status: 'In Progress',
        assignee: null
      },
      {
        id: 2,
        name: 'Site Lease',
        files_count: 1,
        status: 'Reviewing final notes',
        assignee: {
          id: 1,
          first_name: 'John',
          last_name: 'Doe'
        }
      }
    ],
    related_sections: [],
    completed_tasks_percentage: 71.57
  }
];

describe('RecursiveAccordion component', () => {
  test('renders the component', () => {
    render(
      <BrowserRouter>
        <RecursiveAccordion items={diligenceDocumentsMock} />
      </BrowserRouter>
    );

    const accordionItems = screen.getAllByTestId('accordion-item__component');

    expect(accordionItems.length).toBe(2);
  });
});

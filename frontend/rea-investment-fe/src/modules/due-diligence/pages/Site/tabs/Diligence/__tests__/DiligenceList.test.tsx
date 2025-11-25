import { screen, render, act, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider, queryOptions } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { siteDiligenceQuery } from '../../../loader';
import DiligenceList from '../DiligenceList';

const diligenceDocumentsMock = JSON.parse(`
  {
    "items": [
      {
        "name": "Executive Summary",
        "documents_count": 1,
        "documents": [
          {
            "id": 1,
            "name": "Executive summary",
            "files_count": 22,
            "status": "Reviewing final notes",
            "assignee": null
          }
        ],
        "related_sections": [],
        "completed_tasks_percentage": 15.01
      },
      {
        "name": "Preview",
        "documents_count": 3,
        "documents": [
          {
            "id": 5,
            "name": "EPC Agreement",
            "files_count": 3,
            "status": "In Progress",
            "assignee": {
              "id": 1,
              "first_name": "John",
              "last_name": "Doe"
            }
          },
          {
            "id": 4,
            "name": "O&M Agreement",
            "files_count": 0,
            "status": "In Progress",
            "assignee": null
          },
          {
            "id": 2,
            "name": "Site Lease",
            "files_count": 1,
            "status": "Reviewing final notes",
            "assignee": {
              "id": 1,
              "first_name": "John",
              "last_name": "Doe"
            }
          }
        ],
        "related_sections": [],
        "completed_tasks_percentage": 71.57
      }
    ]
  }
`);

jest.mock('react-router-dom', () => ({
  useNavigate: jest.fn(),
  useParams: jest.fn()
}));

jest.mock('../../../loader', () => ({
  siteDiligenceQuery: jest.fn()
}));

describe('DiligenceList component', () => {
  it('should render and function correctly', async () => {
    const queryClient = new QueryClient();
    const navigateMockFn = jest.fn();

    if (jest.isMockFunction(siteDiligenceQuery)) {
      siteDiligenceQuery.mockReturnValue(
        queryOptions({
          queryKey: ['site', 'diligence'],
          queryFn: () => Promise.resolve(diligenceDocumentsMock),
          enabled: true
        })
      );
    }

    if (jest.isMockFunction(useNavigate)) {
      useNavigate.mockReturnValue(navigateMockFn);
    }

    if (jest.isMockFunction(useParams)) {
      useParams.mockReturnValue({
        siteId: 12,
        companyId: 4
      });
    }

    await act(() =>
      render(
        <QueryClientProvider client={queryClient}>
          <DiligenceList />
        </QueryClientProvider>
      )
    );

    await waitFor(() => {
      expect(screen.getByText('Preview (3)')).toBeInTheDocument();
      expect(screen.getByText('72%')).toBeInTheDocument();
      expect(screen.getByText('O&M Agreement')).toBeInTheDocument();
      expect(screen.getAllByText('Reviewing final notes').length).toBe(2);
    });

    const [openBtn] = screen.getAllByRole('button', {
      name: /open/i
    });
    fireEvent.click(openBtn);

    await waitFor(() => {
      expect(navigateMockFn).toHaveBeenCalledTimes(1);
    });
  });
});

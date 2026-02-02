import { screen, render, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider, queryOptions } from '@tanstack/react-query';

import { companyBoardsQuery, taskDetailsQuery, companyDetailsQuery } from '../loader';

import CompanyTaskPage from '../CompanyTask';

jest.mock('../../../../../components/common/DocumentList/DocumentList', () => ({
  __esModule: true,
  default: () => <div>DocumentList-section-placeholder</div>
}));

jest.mock('../../../../../components/forms/TaskComments/TaskComments', () => ({
  __esModule: true,
  default: () => <div>TaskComments-section-placeholder</div>
}));

jest.mock('../../../../../components/forms/TaskDescription/TaskDescription', () => ({
  __esModule: true,
  default: () => <div>TaskDescription-section-placeholder</div>
}));

jest.mock('../../../../../components/forms/TaskDetails/TaskDetails', () => ({
  __esModule: true,
  default: () => <div>TaskDetails-section-placeholder</div>
}));

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useParams: () => ({ taskId: 3, companyId: 4 }),
  useSearchParams: () => [new URLSearchParams({ editOnLanding: 'true' }), jest.fn()]
}));

jest.mock('../loader', () => ({
  companyBoardsQuery: jest.fn(),
  taskDetailsQuery: jest.fn(),
  companyDetailsQuery: jest.fn()
}));

describe('CompanyTaskPage component', () => {
  it('should render and function correctly', async () => {
    const queryClient = new QueryClient();

    if (jest.isMockFunction(companyDetailsQuery)) {
      companyDetailsQuery.mockReturnValue(
        queryOptions({
          queryKey: ['company', 'details'],
          queryFn: () => Promise.resolve({}),
          enabled: true
        })
      );
    }

    if (jest.isMockFunction(companyBoardsQuery)) {
      companyBoardsQuery.mockReturnValue(
        queryOptions({
          queryKey: ['task-boards'],
          queryFn: () => Promise.resolve({ items: [{ id: 225 }] }),
          enabled: true
        })
      );
    }

    if (jest.isMockFunction(taskDetailsQuery)) {
      taskDetailsQuery.mockReturnValue(
        queryOptions({
          queryKey: ['tasks', 'details'],
          queryFn: () =>
            Promise.resolve({
              name: 'Review inverter #18',
              description: 'Please, investigate and document inverter #18 metrics',
              priority: 'High',
              due_date: '2024-07-06',
              id: 11,
              external_id: 'TG-11'
            }),
          enabled: true
        })
      );
    }

    await act(() =>
      render(
        <QueryClientProvider client={queryClient}>
          <CompanyTaskPage />
        </QueryClientProvider>
      )
    );

    await waitFor(() => {
      expect(screen.getByText('TG-11: Review inverter #18')).toBeInTheDocument();
    });

    expect(screen.getByText('TaskDetails-section-placeholder')).toBeInTheDocument();
    expect(screen.getByText('DocumentList-section-placeholder')).toBeInTheDocument();
    expect(screen.getByText('TaskComments-section-placeholder')).toBeInTheDocument();
    expect(screen.getByText('TaskDescription-section-placeholder')).toBeInTheDocument();
  });
});

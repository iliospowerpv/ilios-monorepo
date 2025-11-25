import { screen, render, act, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AssigneeSearchField } from '../AssigneeSearchField';
import { ApiClient } from '../../../../api';

const potentialTaskAssigneesMock = JSON.parse(`
  {
    "items": [
        {
            "id": 185,
            "first_name": "Liubov",
            "last_name": "Mykhailova"
        },
        {
            "id": 4,
            "first_name": "Nat Test",
            "last_name": "System Admin"
        },
        {
            "id": 198,
            "first_name": "Test",
            "last_name": "Release"
        },
        {
            "id": 2,
            "first_name": "Yulian",
            "last_name": "Terletskyi"
        },
        {
            "id": 178,
            "first_name": "Yurii",
            "last_name": "Kostiv"
        }
    ]
  }
`);

jest.mock('../../../../contexts/notifications/notifications', () => ({
  useNotify: () => jest.fn()
}));

jest.mock('../../../../api', () => ({
  ApiClient: {
    taskManagement: {
      potentialTaskAssignees: jest.fn()
    }
  }
}));

describe('AssigneeSearchField component', () => {
  it('should render and function correctly', async () => {
    const queryClient = new QueryClient();
    const onChangeMockFn = jest.fn();
    const assignedUserMock = {
      id: 2,
      first_name: 'Yulian',
      last_name: 'Terletskyi'
    };

    if (jest.isMockFunction(ApiClient.taskManagement.potentialTaskAssignees)) {
      ApiClient.taskManagement.potentialTaskAssignees.mockImplementation((...args: [number, { search: string }]) => {
        const [, params] = args;
        const { search } = params;

        if (!search) {
          return Promise.resolve(potentialTaskAssigneesMock);
        } else {
          const filteredBySearchTerm = potentialTaskAssigneesMock.items.filter(
            (item: { first_name: string; last_name: string }) =>
              item.first_name.includes(search) || item.last_name.includes(search)
          );
          return Promise.resolve({ items: filteredBySearchTerm });
        }
      });
    }

    await act(() =>
      render(
        <QueryClientProvider client={queryClient}>
          <AssigneeSearchField value={assignedUserMock} boardId={5} onChange={onChangeMockFn} />
        </QueryClientProvider>
      )
    );

    await waitFor(() => {
      expect(ApiClient.taskManagement.potentialTaskAssignees).toHaveBeenCalledTimes(2);
      expect(ApiClient.taskManagement.potentialTaskAssignees).toHaveBeenLastCalledWith(5, { search: '' });
    });

    const assigneeSearchInput = screen.getByRole('combobox');
    expect(assigneeSearchInput).toBeInTheDocument();
    expect(assigneeSearchInput).toHaveValue('Yulian Terletskyi');

    const openBtn = screen.getByLabelText('Open');
    fireEvent.click(openBtn);

    await waitFor(() => {
      const assigneeOption = screen.getByText('Liubov Mykhailova');
      expect(assigneeOption).toBeInTheDocument();
      fireEvent.click(assigneeOption);
    });

    await waitFor(() => {
      expect(onChangeMockFn).toHaveBeenCalledTimes(1);
      expect(onChangeMockFn.mock.calls[0][1]).toEqual({ first_name: 'Liubov', id: 185, last_name: 'Mykhailova' });
    });
  });
});

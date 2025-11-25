import { screen, render, act, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from '@mui/material/styles';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { TaskDetails } from '../TaskDetails';
import { ApiClient } from '../../../../api';
import theme from '../../../../utils/styles/theme';

const taskDataMock = JSON.parse(`
  {
    "name": "Test task",
    "description": "Plain description of a task",
    "priority": "Medium",
    "due_date": "2024-07-29",
    "id": 267,
    "external_id": "TG-267",
    "affected_device": null,
    "creator": {
        "id": 2,
        "first_name": "Yulian",
        "last_name": "Terletskyi"
    },
    "assignee": {
        "id": 301,
        "first_name": "Another",
        "last_name": "Testacc"
    },
    "status": {
        "id": 1727,
        "name": "Completed"
    }
  }
`);

const boardStatusesMock = JSON.parse(`
  {
    "items": [
        {
            "name": "Assigned",
            "id": 1724
        },
        {
            "name": "Cancelled",
            "id": 1729
        },
        {
            "name": "Closed",
            "id": 1728
        },
        {
            "name": "Completed",
            "id": 1727
        },
        {
            "name": "Escalated",
            "id": 1726
        },
        {
            "name": "In Process",
            "id": 1725
        },
        {
            "name": "New",
            "id": 1723
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
      updateTask: jest.fn(),
      getStatuses: jest.fn()
    }
  }
}));

jest.mock('../../AssigneeSearchField/AssigneeSearchField', () => ({
  __esModule: true,
  default: (props: { value: null | { first_name: string; last_name: string } }) => (
    <div>{props.value ? `${props.value.first_name} ${props.value.last_name}` : null}</div>
  )
}));

describe('TaskDetails component', () => {
  it('should render and function correctly', async () => {
    const queryClient = new QueryClient();

    if (jest.isMockFunction(ApiClient.taskManagement.updateTask)) {
      ApiClient.taskManagement.updateTask.mockResolvedValue({ code: 200, message: 'Success' });
    }

    if (jest.isMockFunction(ApiClient.taskManagement.getStatuses)) {
      ApiClient.taskManagement.getStatuses.mockResolvedValue(boardStatusesMock);
    }

    await act(() =>
      render(
        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <QueryClientProvider client={queryClient}>
            <ThemeProvider theme={theme}>
              <TaskDetails taskData={taskDataMock} boardId={5} scope="site" siteName="Test site 2" siteId={23} />
            </ThemeProvider>
          </QueryClientProvider>
        </LocalizationProvider>
      )
    );

    expect(screen.getByText('Test task')).toBeInTheDocument();
    expect(screen.getByText('Medium')).toBeInTheDocument();
    expect(screen.getByText('07/29/2024')).toBeInTheDocument();
    expect(screen.getByText('Yulian Terletskyi')).toBeInTheDocument();
    expect(screen.getByText('Test site 2')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();

    const editBtn = screen.getByTestId('task_details-details-edit_btn');
    fireEvent.click(editBtn);

    await waitFor(() => {
      const taskNameInput = screen.getByDisplayValue('Test task');
      fireEvent.change(taskNameInput, { target: { value: 'another task name (updated)' } });
    });

    await waitFor(() => {
      const saveButton = screen.getByText('Save');
      expect(saveButton).toBeEnabled();
      fireEvent.click(saveButton);
    });

    await waitFor(() => {
      expect(ApiClient.taskManagement.updateTask).toHaveBeenCalledTimes(1);
      expect(ApiClient.taskManagement.updateTask).toHaveBeenCalledWith(5, 267, {
        assignee_id: 301,
        due_date: '2024-07-29',
        name: 'another task name (updated)',
        priority: 'Medium',
        status_id: 1727,
        affected_device_id: null
      });
    });

    expect(editBtn).toBeVisible();
    fireEvent.click(editBtn);

    await waitFor(() => {
      expect(editBtn).not.toBeVisible();
      const taskNameInput = screen.getByDisplayValue('another task name (updated)');
      fireEvent.change(taskNameInput, { target: { value: 'updated again' } });
    });

    await waitFor(() => {
      const cancelButton = screen.getByText('Cancel');
      expect(cancelButton).toBeEnabled();
      fireEvent.click(cancelButton);
    });

    await waitFor(() => {
      expect(editBtn).toBeVisible();
    });
  });
});

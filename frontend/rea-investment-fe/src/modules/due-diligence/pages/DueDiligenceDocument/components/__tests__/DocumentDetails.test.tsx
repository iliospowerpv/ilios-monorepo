import React from 'react';
import { screen, render, act, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { ThemeProvider } from '@mui/material/styles';
import { DocumentDetails } from '../DocumentDetails';
import { ApiClient } from '../../../../../../api';
import theme from '../../../../../../utils/styles/theme';

const documentDataMock = JSON.parse(`
  {
    "id": 1,
    "name": "Executive summary",
    "type": "Diligence",
    "site": {
        "id": 4,
        "name": "Demo Site 1235",
        "address": "110 Shawmut Road"
    },
    "section": {
        "id": 1,
        "name": "Executive Summary"
    },
    "description": "just plain description updated",
    "approver": {
        "id": 198,
        "first_name": "Yulian",
        "last_name": "Terletskyi"
    },
    "task": {
        "id": 318,
        "board_id": 513,
        "name": "Default task for board #513",
        "priority": "High",
        "due_date": "2024-09-28",
        "assignee": null,
        "status": {
            "id": 2833,
            "name": "Completed"
        }
    }
  }
`);

jest.mock('../../../../../../contexts/notifications/notifications', () => ({
  useNotify: () => jest.fn()
}));

jest.mock('../../../../../../api', () => ({
  ApiClient: {
    dueDiligence: {
      updateDocumentDetails: jest.fn()
    }
  }
}));

jest.mock('../../../../../../components/forms/AssigneeSearchField/AssigneeSearchField', () => {
  const { forwardRef } = jest.requireActual('react');
  const { default: TextField } = jest.requireActual('@mui/material/TextField');
  const AssigneeSearchFieldStub = forwardRef((props: any, ref: any) => (
    <TextField
      {...props}
      ref={ref}
      value={props.value ? `${props.value.first_name} ${props.value.last_name}` : null}
      onChange={(e: { target: { value: any } }) => {
        const [first_name, last_name] = typeof e.target.value === 'string' ? e.target.value.split(' ') : ['no', 'user'];
        props.onChange && props.onChange(e, { first_name, last_name, id: 13 });
      }}
    />
  ));

  return {
    __esModule: true,
    default: AssigneeSearchFieldStub
  };
});

describe('DocumentDetails component', () => {
  it('should render and function correctly', async () => {
    const queryClient = new QueryClient();

    if (jest.isMockFunction(ApiClient.dueDiligence.updateDocumentDetails)) {
      ApiClient.dueDiligence.updateDocumentDetails.mockResolvedValue({ code: 200, message: 'Success' });
    }

    await act(() =>
      render(
        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <QueryClientProvider client={queryClient}>
            <ThemeProvider theme={theme}>
              <DocumentDetails boardId={513} siteId={4} documentId={1} documentInfo={documentDataMock} />
            </ThemeProvider>
          </QueryClientProvider>
        </LocalizationProvider>
      )
    );

    expect(screen.getByText('Demo Site 1235')).toBeInTheDocument();
    expect(screen.getByText('Diligence')).toBeInTheDocument();
    expect(screen.getByText('Executive Summary')).toBeInTheDocument();
    expect(screen.getByText('Yulian Terletskyi')).toBeInTheDocument();

    const editBtn = screen.getByTestId('document_details-details-edit_btn');
    fireEvent.click(editBtn);

    await waitFor(() => {
      const taskNameInput = screen.getByDisplayValue('Yulian Terletskyi');
      fireEvent.change(taskNameInput, { target: { value: 'Another User' } });
    });

    await waitFor(() => {
      const saveButton = screen.getByText('Save');
      expect(saveButton).toBeEnabled();
      fireEvent.click(saveButton);
    });

    await waitFor(() => {
      expect(ApiClient.dueDiligence.updateDocumentDetails).toHaveBeenCalledTimes(1);
      expect(ApiClient.dueDiligence.updateDocumentDetails).toHaveBeenCalledWith({
        attributes: { approver_id: 13 },
        documentId: 1,
        siteId: 4
      });
    });

    expect(editBtn).toBeVisible();
    fireEvent.click(editBtn);

    await waitFor(() => {
      expect(editBtn).not.toBeVisible();
      const taskNameInput = screen.getByDisplayValue('Another User');
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

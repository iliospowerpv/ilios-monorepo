import { screen, render, act, waitFor } from '@testing-library/react';
import { DueDiligenceDocumentPage } from '../DueDiligenceDocument';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NotificationsProvider } from '../../../../../contexts/notifications/notifications';

jest.mock('react-router-dom', () => ({
  useParams: () => ({
    documentId: '22',
    siteId: '7'
  })
}));

jest.mock('../../../../../api', () => ({
  ApiClient: {
    dueDiligence: {
      docInfo: () =>
        Promise.resolve(
          JSON.parse(`
            {
              "id": 1,
              "name": "Executive Summary",
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
          `)
        )
    }
  }
}));

jest.mock('../../../../../components/forms/TaskDetails/TaskDetails', () => ({
  __esModule: true,
  default: () => <div>TaskDetails-component-placeholder</div>
}));

jest.mock('../components/DocumentDetails', () => ({
  __esModule: true,
  default: () => <div>DocumentDetails-component-placeholder</div>
}));

jest.mock('../components/DocumentDescription', () => ({
  __esModule: true,
  default: () => <div>DocumentDescription-component-placeholder</div>
}));

jest.mock('../components/DocumentComments', () => ({
  __esModule: true,
  default: () => <div>DocumentComments-component-placeholder</div>
}));

describe('DueDiligenceDocumentPage component', () => {
  it('should render component correctly', async () => {
    const queryClient = new QueryClient();
    await act(() =>
      render(
        <QueryClientProvider client={queryClient}>
          <NotificationsProvider>
            <DueDiligenceDocumentPage />
          </NotificationsProvider>
        </QueryClientProvider>
      )
    );

    await waitFor(() => {
      expect(screen.getByText('Executive Summary')).toBeInTheDocument();
      expect(screen.getByText('TaskDetails-component-placeholder')).toBeInTheDocument();
      expect(screen.getByText('DocumentDetails-component-placeholder')).toBeInTheDocument();
      expect(screen.getByText('DocumentDescription-component-placeholder')).toBeInTheDocument();
      expect(screen.getByText('DocumentComments-component-placeholder')).toBeInTheDocument();
    });
  });
});

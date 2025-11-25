import { screen, render, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DocumentDescription } from '../DocumentDescription';
import { ApiClient } from '../../../../../../api';

jest.mock('../../../../../../contexts/notifications/notifications', () => ({
  useNotify: () => jest.fn()
}));

jest.mock('../../../../../../contexts/auth/auth', () => ({
  useAuth: () => ({
    user: {
      first_name: 'Rob',
      last_name: 'Pike'
    }
  })
}));

jest.mock('../../../../../../api', () => ({
  ApiClient: {
    dueDiligence: {
      updateDocDescription: jest.fn()
    }
  }
}));

describe('DocumentDescription component', () => {
  it('should render component correctly', async () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DocumentDescription documentId={22} siteId={7} descriptionText={null} />
      </QueryClientProvider>
    );

    const descriptionInputArea = screen.getByPlaceholderText('Add description…');
    expect(descriptionInputArea).toBeInTheDocument();
  });

  it('should invoke updateDocDescription API call when user tries to add description', async () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DocumentDescription documentId={22} siteId={7} descriptionText={null} />
      </QueryClientProvider>
    );

    const descriptionInputArea = screen.getByPlaceholderText('Add description…');
    expect(descriptionInputArea).toBeInTheDocument();
    fireEvent.change(descriptionInputArea, { target: { value: 'A plain description' } });

    await waitFor(() => {
      const saveButton = screen.getByText('Save');
      expect(saveButton).toBeEnabled();
      fireEvent.click(saveButton);
    });

    await waitFor(() => {
      expect(ApiClient.dueDiligence.updateDocDescription).toHaveBeenCalledTimes(1);
      expect(ApiClient.dueDiligence.updateDocDescription).toHaveBeenCalledWith(7, 22, 'A plain description');
    });
  });

  it('should disable description editing until user intentionally clicks on edit button when description is already filled', async () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <DocumentDescription documentId={22} siteId={7} descriptionText="A plain description" />
      </QueryClientProvider>
    );

    const descriptionInputArea = screen.getByDisplayValue('A plain description');
    expect(descriptionInputArea).toBeInTheDocument();
    expect(descriptionInputArea).toBeDisabled();

    const editDescriptionBtn = screen.getByTestId('document_details-description-edit_btn');
    expect(editDescriptionBtn).toBeInTheDocument();
    fireEvent.click(editDescriptionBtn);

    await waitFor(() => {
      expect(descriptionInputArea).toBeEnabled();
    });
  });
});

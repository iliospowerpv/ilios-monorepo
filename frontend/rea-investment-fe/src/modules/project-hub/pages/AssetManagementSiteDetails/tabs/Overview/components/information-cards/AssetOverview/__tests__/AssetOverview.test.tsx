import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { AssetOverviewCard } from '../AssetOverview';

jest.mock('../../../../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn()
}));

describe('AssetOverview Card form component', () => {
  const queryClient = new QueryClient();

  it('renders and functions correctly', async () => {
    const data = {
      battery_storage: 'Yes',
      module_quantity: '1',
      inverter_quantity: '2',
      project_type: 'test',
      mount_type: 'test2'
    };

    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <AssetOverviewCard siteId={5} data={data} />
        </QueryClientProvider>
      </BrowserRouter>
    );

    const editBtn = screen.getByTestId('asset_overview-edit-btn');

    fireEvent.click(editBtn);

    await waitFor(() => {
      expect(screen.getAllByRole('combobox').length).toBe(1);
    });
  });
});

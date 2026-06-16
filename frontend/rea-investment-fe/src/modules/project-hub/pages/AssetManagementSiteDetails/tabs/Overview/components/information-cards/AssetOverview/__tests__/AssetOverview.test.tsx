import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { AssetOverviewCard } from '../AssetOverview';

jest.mock('../../../../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn()
}));

jest.mock('../../../../../../../../../../contexts/auth/auth', () => ({
  useAuth: () => ({ user: { is_system_user: true } })
}));

describe('AssetOverview Card form component', () => {
  const queryClient = new QueryClient();

  const data = {
    battery_storage: 'Yes',
    module_quantity: '1',
    inverter_quantity: '2',
    project_type: 'test',
    mount_type: 'test2',
    dc_wiring_loss: 1.5,
    ac_wiring_loss: 1,
    medium_voltage_loss: 0.5,
    mv_line_loss: 0.25
  };

  const renderCard = () =>
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <AssetOverviewCard siteId={5} data={data} />
        </QueryClientProvider>
      </BrowserRouter>
    );

  it('renders baseline-driving fields read-only with provenance labels and a Data Room link', () => {
    renderCard();

    // The four ohmic-loss fields carry the baseline-driving provenance note.
    expect(screen.getAllByText(/Baseline-driving/i).length).toBe(4);
    // Module/Inverter quantity and Project Type carry the source provenance note.
    expect(screen.getAllByText(/Source: Data Room/i).length).toBe(3);
    // Read-only nav link to the Data Room (no mutation buttons).
    expect(screen.getByRole('link', { name: /open data room/i })).toBeTruthy();
  });

  it('keeps baseline-driving fields read-only after entering edit mode', async () => {
    renderCard();

    fireEvent.click(screen.getByTestId('asset_overview-edit-btn'));

    // Edit mode is active (ordinary metadata such as Mount Type / Battery Storage is editable).
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /save/i })).toBeTruthy();
    });
    expect(screen.getByRole('button', { name: /cancel/i })).toBeTruthy();

    // Baseline-driving fields remain read-only in edit mode (provenance notes still shown).
    expect(screen.getAllByText(/Baseline-driving/i).length).toBe(4);
    expect(screen.getAllByText(/Source: Data Room/i).length).toBe(3);
  });
});

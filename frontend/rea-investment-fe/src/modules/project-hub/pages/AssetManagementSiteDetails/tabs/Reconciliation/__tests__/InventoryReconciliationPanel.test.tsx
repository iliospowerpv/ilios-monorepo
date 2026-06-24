import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import type {
  InventoryAckListResponse,
  InventoryAckResponse,
  InventoryMismatch,
  InventoryMismatchTrackedStatusResponse,
  InventoryMismatchTrackedTask,
  InventoryReconciliationResponse
} from '../../../../../../../types/telemetryV2';

// Mock the API client index so the panel resolves through our spies instead of
// hitting axios. The factory may only reference `mock`-prefixed outer variables.
const mockGetRecon = jest.fn();
const mockListAcks = jest.fn();
const mockCreateAck = jest.fn();
const mockRevokeAck = jest.fn();
const mockGetTracked = jest.fn();
jest.mock('../../../../../../../api', () => ({
  ApiClient: {
    telemetryV2: {
      getSiteInventoryReconciliation: (...args: unknown[]) => mockGetRecon(...args),
      listInventoryAcknowledgements: (...args: unknown[]) => mockListAcks(...args),
      createInventoryAcknowledgement: (...args: unknown[]) => mockCreateAck(...args),
      revokeInventoryAcknowledgement: (...args: unknown[]) => mockRevokeAck(...args),
      getInventoryReconciliationTrackedTasks: (...args: unknown[]) => mockGetTracked(...args)
    }
  }
}));

// useAuth() throws without an AuthProvider, so mock it. A jest.fn lets each test
// flip between a reviewer (Asset.edit) and a read-only viewer.
const mockUseAuth = jest.fn();
jest.mock('../../../../../../../contexts/auth/auth', () => ({
  useAuth: () => mockUseAuth()
}));

// Imported after jest.mock so the component picks up the mocked ApiClient.
import InventoryReconciliationPanel from '../components/InventoryReconciliationPanel';

const RECON_VERSION = 'inv-recon/1';

const baseMismatch = (overrides: Partial<InventoryMismatch> = {}): InventoryMismatch => ({
  mismatch_signature: 'sig-acknowledgeable',
  category: 'quantity_mismatch',
  equipment_class: 'inverter',
  acknowledgement_policy: 'acknowledgeable_non_blocking',
  blocking_level: 'lowers_confidence',
  title: 'Inverter count differs',
  detail: 'Documented 10, observed 9.',
  recommended_action: 'Confirm the as-built inverter count.',
  next_step_target: null,
  device_id: null,
  device_name: null,
  recorded_provenance: null,
  reconciliation_inference: null,
  documented_value: '10',
  observed_value: '9',
  weather_subtype: null,
  coverage_mode: null,
  active_fact_ids: [],
  candidate_fact_ids: [],
  external_device_id: null,
  is_acknowledged: false,
  ...overrides
});

const buildResponse = (mismatches: InventoryMismatch[]): InventoryReconciliationResponse => ({
  site_id: 123,
  generated_at: '2026-06-12T08:00:00Z',
  status: 'needs_reconciliation',
  status_label: 'Needs reconciliation',
  status_explanation: 'There are open actionable mismatches.',
  telemetry_connected: true,
  site_mapped: true,
  documented_inventory_state: 'complete',
  documented_inventory_incomplete: false,
  discovery_stale: false,
  discovery_last_synced_at: '2026-06-12T07:00:00Z',
  has_blocking_mismatch: false,
  weather_dependency_unsatisfied: false,
  weather_dependency_subtype: 'not_applicable',
  active_expected_baseline_id: null,
  active_expected_baseline_requires_weather: false,
  coverage_mode: 'device_level',
  total_ilios_devices: 10,
  total_discovered_devices: 9,
  class_counts: [],
  mismatch_category_counts: {},
  open_actionable_mismatch_count: mismatches.filter(m => !m.is_acknowledged).length,
  informational_mismatch_count: 0,
  acknowledged_exception_count: mismatches.filter(m => m.is_acknowledged).length,
  mismatches,
  next_actions: [],
  notes: [],
  reconciliation_version: RECON_VERSION
});

const buildAckList = (acks: InventoryAckResponse[] = []): InventoryAckListResponse => ({
  site_id: 123,
  reconciliation_version: RECON_VERSION,
  acknowledgements: acks
});

const activeAck = (signature: string): InventoryAckResponse => ({
  id: 55,
  site_id: 123,
  mismatch_signature: signature,
  reconciliation_version: RECON_VERSION,
  mismatch_type: 'quantity_mismatch',
  severity: 'lowers_confidence',
  acknowledgement_policy: 'acknowledgeable_non_blocking',
  mismatch_title: 'Inverter count differs',
  mismatch_detail: 'Documented 10, observed 9.',
  source_module: 'device_inventory_reconciliation',
  acknowledged_context_hash: null,
  status: 'acknowledged',
  acknowledged_by: 7,
  acknowledged_at: '2026-06-12T09:00:00Z',
  acknowledgement_reason: 'Verified against the as-built drawings.',
  revoked_by: null,
  revoked_at: null,
  revocation_reason: null,
  created_at: '2026-06-12T09:00:00Z',
  updated_at: '2026-06-12T09:00:00Z',
  is_active: true,
  is_expired: false
});

const trackedTask = (signature: string, overrides: Partial<InventoryMismatchTrackedTask> = {}): InventoryMismatchTrackedTask => ({
  mismatch_signature: signature,
  is_tracked: true,
  task_id: 99,
  task_name: 'Inventory: confirm inverter count',
  task_status: 'To Do',
  task_link: '/project-hub/companies/3/sites/123/tasks/99',
  ...overrides
});

const buildTracked = (tracked: InventoryMismatchTrackedTask[] = []): InventoryMismatchTrackedStatusResponse => ({
  tracked
});

const renderPanel = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <InventoryReconciliationPanel siteId={123} />
      </QueryClientProvider>
    </MemoryRouter>
  );
};

beforeEach(() => {
  jest.clearAllMocks();
  mockListAcks.mockResolvedValue(buildAckList());
  // No tracking tasks by default — rows fall back to "Create task".
  mockGetTracked.mockResolvedValue(buildTracked());
  // Default to a reviewer with Asset.edit rights.
  mockUseAuth.mockReturnValue({
    user: { is_system_user: false, role: { permissions: { 'Asset Management': { edit: true } } } }
  });
});

describe('InventoryReconciliationPanel acknowledgements', () => {
  it('offers an Acknowledge action for an acknowledgeable mismatch to a reviewer', async () => {
    mockGetRecon.mockResolvedValue(buildResponse([baseMismatch()]));

    renderPanel();

    expect(await screen.findByTestId('inventory-ack-sig-acknowledgeable')).toBeInTheDocument();
  });

  it('never offers acknowledgement for a blocking mismatch', async () => {
    mockGetRecon.mockResolvedValue(
      buildResponse([
        baseMismatch({
          mismatch_signature: 'sig-blocking',
          acknowledgement_policy: 'not_acknowledgeable_blocking',
          blocking_level: 'blocks_calculation',
          title: 'Weather dependency unsatisfied'
        })
      ])
    );

    renderPanel();

    expect(await screen.findByText('Cannot acknowledge')).toBeInTheDocument();
    expect(screen.queryByTestId('inventory-ack-sig-blocking')).not.toBeInTheDocument();
  });

  it('hides the Acknowledge action from a read-only viewer', async () => {
    mockUseAuth.mockReturnValue({
      user: { is_system_user: false, role: { permissions: { 'Asset Management': { edit: false } } } }
    });
    mockGetRecon.mockResolvedValue(buildResponse([baseMismatch()]));

    renderPanel();

    // Wait for the loaded row content; a read-only viewer sees the gating caption
    // instead of an Acknowledge button.
    expect(await screen.findByText('Asset edit required')).toBeInTheDocument();
    expect(screen.queryByTestId('inventory-ack-sig-acknowledgeable')).not.toBeInTheDocument();
  });

  it('submits an acknowledgement with the exact signature and reconciliation_version', async () => {
    mockGetRecon.mockResolvedValue(buildResponse([baseMismatch()]));
    mockCreateAck.mockResolvedValue(activeAck('sig-acknowledgeable'));

    renderPanel();

    fireEvent.click(await screen.findByTestId('inventory-ack-sig-acknowledgeable'));

    const reasonInput = await screen.findByTestId('inventory-ack-reason');
    fireEvent.change(reasonInput, { target: { value: 'Verified against the as-built drawings.' } });
    fireEvent.click(screen.getByTestId('inventory-ack-confirm'));

    await waitFor(() => expect(mockCreateAck).toHaveBeenCalledTimes(1));
    expect(mockCreateAck).toHaveBeenCalledWith(123, {
      mismatch_signature: 'sig-acknowledgeable',
      reconciliation_version: RECON_VERSION,
      acknowledgement_reason: 'Verified against the as-built drawings.'
    });
  });

  it('disables confirm until the reason meets the minimum length', async () => {
    mockGetRecon.mockResolvedValue(buildResponse([baseMismatch()]));

    renderPanel();

    fireEvent.click(await screen.findByTestId('inventory-ack-sig-acknowledgeable'));
    const confirm = screen.getByTestId('inventory-ack-confirm');
    expect(confirm).toBeDisabled();

    fireEvent.change(screen.getByTestId('inventory-ack-reason'), { target: { value: 'short' } });
    expect(confirm).toBeDisabled();

    fireEvent.change(screen.getByTestId('inventory-ack-reason'), {
      target: { value: 'A sufficiently detailed reason.' }
    });
    expect(confirm).not.toBeDisabled();
  });

  it('shows an Acknowledged chip and a Revoke action for an already-acknowledged mismatch', async () => {
    mockGetRecon.mockResolvedValue(buildResponse([baseMismatch({ is_acknowledged: true })]));
    mockListAcks.mockResolvedValue(buildAckList([activeAck('sig-acknowledgeable')]));
    mockRevokeAck.mockResolvedValue({ ...activeAck('sig-acknowledgeable'), status: 'revoked', is_active: false });

    renderPanel();

    expect(await screen.findByText('Acknowledged')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('inventory-ack-revoke-sig-acknowledgeable'));

    fireEvent.change(await screen.findByTestId('inventory-revoke-reason'), {
      target: { value: 'New evidence invalidates this exception.' }
    });
    fireEvent.click(screen.getByTestId('inventory-revoke-confirm'));

    await waitFor(() => expect(mockRevokeAck).toHaveBeenCalledTimes(1));
    expect(mockRevokeAck).toHaveBeenCalledWith(123, 55, {
      revocation_reason: 'New evidence invalidates this exception.'
    });
  });

  it('surfaces a server error message inside the acknowledge dialog', async () => {
    mockGetRecon.mockResolvedValue(buildResponse([baseMismatch()]));
    mockCreateAck.mockRejectedValue({ response: { data: { detail: 'Reconciliation version is stale.' } } });

    renderPanel();

    fireEvent.click(await screen.findByTestId('inventory-ack-sig-acknowledgeable'));
    fireEvent.change(await screen.findByTestId('inventory-ack-reason'), {
      target: { value: 'Verified against the as-built drawings.' }
    });
    fireEvent.click(screen.getByTestId('inventory-ack-confirm'));

    expect(await screen.findByTestId('inventory-ack-dialog-error')).toHaveTextContent(
      'Reconciliation version is stale.'
    );
  });
});

describe('InventoryReconciliationPanel tracked-task indicator', () => {
  it('shows a Tracked deep link (and no Create task) when an open task tracks the mismatch', async () => {
    mockGetRecon.mockResolvedValue(buildResponse([baseMismatch()]));
    mockGetTracked.mockResolvedValue(buildTracked([trackedTask('sig-acknowledgeable')]));

    renderPanel();

    const chip = await screen.findByTestId('inventory-tracked-chip');
    expect(chip).toBeInTheDocument();
    expect(chip.closest('a')).toHaveAttribute('href', '/project-hub/companies/3/sites/123/tasks/99');
    // Never both: the Create task button must be absent for a tracked row.
    expect(screen.queryByTestId('inventory-create-task-button')).not.toBeInTheDocument();
  });

  it('shows Create task (and no Tracked chip) when no open task tracks the mismatch', async () => {
    mockGetRecon.mockResolvedValue(buildResponse([baseMismatch()]));
    mockGetTracked.mockResolvedValue(buildTracked([]));

    renderPanel();

    expect(await screen.findByTestId('inventory-create-task-button')).toBeInTheDocument();
    expect(screen.queryByTestId('inventory-tracked-chip')).not.toBeInTheDocument();
  });

  it('falls back to Create task (never a false Tracked) when the tracked lookup fails', async () => {
    mockGetRecon.mockResolvedValue(buildResponse([baseMismatch()]));
    mockGetTracked.mockRejectedValue(new Error('tracked lookup failed'));

    renderPanel();

    expect(await screen.findByTestId('inventory-create-task-button')).toBeInTheDocument();
    expect(screen.queryByTestId('inventory-tracked-chip')).not.toBeInTheDocument();
  });

  it('does not request the tracked lookup for a read-only viewer', async () => {
    mockUseAuth.mockReturnValue({
      user: { is_system_user: false, role: { permissions: { 'Asset Management': { edit: false } } } }
    });
    mockGetRecon.mockResolvedValue(buildResponse([baseMismatch()]));

    renderPanel();

    expect(await screen.findByText('Asset edit required')).toBeInTheDocument();
    expect(mockGetTracked).not.toHaveBeenCalled();
  });
});

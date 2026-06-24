import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const mockBoards = jest.fn();
const mockAssignees = jest.fn();
const mockCreateInventoryTask = jest.fn();
jest.mock('../../../../../../../api', () => ({
  ApiClient: {
    taskManagement: {
      boards: (...args: unknown[]) => mockBoards(...args),
      potentialTaskAssignees: (...args: unknown[]) => mockAssignees(...args)
    },
    telemetryV2: {
      createInventoryReconciliationTask: (...args: unknown[]) => mockCreateInventoryTask(...args)
    }
  }
}));

const mockNotify = jest.fn();
jest.mock('../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: () => mockNotify
}));

import CreateInventoryTaskDialog from '../components/CreateInventoryTaskDialog';

const mismatch = {
  mismatch_signature: 'telemetry_freshness:site:discovery_stale',
  category: 'telemetry_freshness',
  equipment_class: null,
  acknowledgement_policy: 'acknowledgeable_non_blocking',
  blocking_level: 'lowers_confidence',
  title: 'Device discovery is stale',
  detail: 'The provider device list has not been re-synced recently.',
  recommended_action: 'Re-sync the provider device list to refresh discovery.',
  next_step_target: 'discovery_sync',
  device_id: null,
  device_name: null,
  recorded_provenance: null,
  reconciliation_inference: null,
  documented_value: null,
  observed_value: null,
  weather_subtype: null,
  coverage_mode: null,
  active_fact_ids: [],
  candidate_fact_ids: [],
  external_device_id: null,
  is_acknowledged: false
} as any;

const renderDialog = (props: Partial<React.ComponentProps<typeof CreateInventoryTaskDialog>> = {}) => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <CreateInventoryTaskDialog open siteId={123} mismatch={mismatch} onClose={jest.fn()} {...props} />
    </QueryClientProvider>
  );
};

beforeEach(() => {
  jest.clearAllMocks();
  mockBoards.mockResolvedValue({
    skip: 0,
    limit: 10,
    total: 1,
    items: [{ id: 88, name: 'Asset', description: null, is_active: true }]
  });
  mockAssignees.mockResolvedValue({ items: [{ id: 3, first_name: 'Ada', last_name: 'Lovelace' }] });
});

describe('CreateInventoryTaskDialog', () => {
  it('prefills the name, provenance description, and derived priority', async () => {
    renderDialog({ siteName: '110 Shawmut' });

    const name = (await screen.findByTestId('create-inventory-task-name')) as HTMLInputElement;
    expect(name.value).toBe('Inventory: Device discovery is stale');

    const description = screen.getByTestId('create-inventory-task-description') as HTMLTextAreaElement;
    expect(description.value).toContain('Inventory reconciliation follow-up for 110 Shawmut.');
    expect(description.value).toContain('telemetry_freshness:site:discovery_stale');
    expect(description.value).toContain('Re-sync the provider device list to refresh discovery.');
    expect(description.value).toContain('Reconciliation itself changes nothing');

    // lowers_confidence → Medium default.
    const priority = screen.getByTestId('create-inventory-task-priority') as HTMLInputElement;
    expect(priority.value).toBe('Medium');

    // The recommended action is surfaced as an info alert.
    expect(screen.getByTestId('create-inventory-task-recommended')).toBeInTheDocument();
  });

  it('resolves the Asset board scoped to the site (for the assignee picker)', async () => {
    renderDialog();
    await screen.findByTestId('create-inventory-task-name');
    expect(mockBoards).toHaveBeenCalledWith('site', 123, { module: 'Asset' });
  });

  it('derives High priority for a calculation-blocking gap', async () => {
    renderDialog({ mismatch: { ...mismatch, blocking_level: 'blocks_calculation' } });
    const priority = (await screen.findByTestId('create-inventory-task-priority')) as HTMLInputElement;
    expect(priority.value).toBe('High');
  });

  it('creates the task with the mismatch signature and form values', async () => {
    mockCreateInventoryTask.mockResolvedValue({
      created: true,
      duplicate: false,
      task_id: 42,
      external_id: 'IOSP1-42',
      board_id: 88,
      mismatch_signature: mismatch.mismatch_signature,
      message: 'Task created.',
      deep_link: '/project-hub/companies/1/sites/123/tasks/42'
    });
    const onClose = jest.fn();
    renderDialog({ onClose });

    await screen.findByTestId('create-inventory-task-name');
    await waitFor(() => expect(screen.getByTestId('create-inventory-task-submit')).not.toBeDisabled());
    fireEvent.click(screen.getByTestId('create-inventory-task-submit'));

    await waitFor(() => expect(mockCreateInventoryTask).toHaveBeenCalledTimes(1));
    const [siteIdArg, payload] = mockCreateInventoryTask.mock.calls[0];
    expect(siteIdArg).toBe(123);
    expect(payload).toMatchObject({
      mismatch_signature: 'telemetry_freshness:site:discovery_stale',
      name: 'Inventory: Device discovery is stale',
      priority: 'Medium',
      assignee_id: null
    });
    expect(payload.due_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(mockNotify).toHaveBeenCalledWith('Task created.');
  });

  it('notifies with the duplicate message when the gap is already tracked', async () => {
    mockCreateInventoryTask.mockResolvedValue({
      created: false,
      duplicate: true,
      task_id: 7,
      external_id: 'IOSP1-7',
      board_id: 88,
      mismatch_signature: mismatch.mismatch_signature,
      message: 'An open task is already tracking this inventory gap.',
      deep_link: '/project-hub/companies/1/sites/123/tasks/7'
    });
    renderDialog();

    await screen.findByTestId('create-inventory-task-name');
    await waitFor(() => expect(screen.getByTestId('create-inventory-task-submit')).not.toBeDisabled());
    fireEvent.click(screen.getByTestId('create-inventory-task-submit'));

    await waitFor(() =>
      expect(mockNotify).toHaveBeenCalledWith('An open task is already tracking this inventory gap.')
    );
  });

  it('surfaces the server error detail on failure', async () => {
    mockCreateInventoryTask.mockRejectedValue({ response: { data: { detail: 'That finding is no longer present.' } } });
    renderDialog();

    await screen.findByTestId('create-inventory-task-name');
    await waitFor(() => expect(screen.getByTestId('create-inventory-task-submit')).not.toBeDisabled());
    fireEvent.click(screen.getByTestId('create-inventory-task-submit'));

    await waitFor(() => expect(mockNotify).toHaveBeenCalledWith('That finding is no longer present.'));
  });

  it('disables submit when the name is cleared', async () => {
    renderDialog();
    const name = (await screen.findByTestId('create-inventory-task-name')) as HTMLInputElement;
    fireEvent.change(name, { target: { value: '' } });
    expect(screen.getByTestId('create-inventory-task-submit')).toBeDisabled();
  });
});

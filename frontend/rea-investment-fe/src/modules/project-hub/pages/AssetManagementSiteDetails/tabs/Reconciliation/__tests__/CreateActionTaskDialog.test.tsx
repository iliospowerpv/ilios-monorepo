import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const mockBoards = jest.fn();
const mockGetStatuses = jest.fn();
const mockAssignees = jest.fn();
const mockCreateTask = jest.fn();
jest.mock('../../../../../../../api', () => ({
  ApiClient: {
    taskManagement: {
      boards: (...args: unknown[]) => mockBoards(...args),
      getStatuses: (...args: unknown[]) => mockGetStatuses(...args),
      potentialTaskAssignees: (...args: unknown[]) => mockAssignees(...args),
      createTask: (...args: unknown[]) => mockCreateTask(...args)
    }
  }
}));

const mockNotify = jest.fn();
jest.mock('../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: () => mockNotify
}));

import CreateActionTaskDialog from '../components/CreateActionTaskDialog';

const row = {
  canonical_field: 'module_capacity_kw',
  display_label: 'Module Capacity (kW)',
  status: 'accepted_not_promoted',
  status_label: 'Accepted, not promoted',
  required_action: 'Promote this value to current assumptions',
  blocking_level: 'blocks_baseline',
  document_id: 5,
  document_version_id: 9
} as any;

const renderDialog = (props: Partial<React.ComponentProps<typeof CreateActionTaskDialog>> = {}) => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <CreateActionTaskDialog open siteId={123} row={row} onClose={jest.fn()} {...props} />
    </QueryClientProvider>
  );
};

beforeEach(() => {
  jest.clearAllMocks();
  mockBoards.mockResolvedValue({
    skip: 0,
    limit: 10,
    total: 1,
    items: [{ id: 77, name: 'Diligence', description: null, is_active: true }]
  });
  mockGetStatuses.mockResolvedValue({
    items: [
      { id: 5, name: 'Done' },
      { id: 1, name: 'To Do' }
    ]
  });
  mockAssignees.mockResolvedValue({ items: [{ id: 3, first_name: 'Ada', last_name: 'Lovelace' }] });
});

describe('CreateActionTaskDialog', () => {
  it('prefills the name, provenance description, and derived priority', async () => {
    renderDialog();

    const name = (await screen.findByTestId('create-task-name')) as HTMLInputElement;
    expect(name.value).toBe('Diligence: Module Capacity (kW)');

    const description = screen.getByTestId('create-task-description') as HTMLTextAreaElement;
    expect(description.value).toContain('module_capacity_kw');
    expect(description.value).toContain('Promote this value to current assumptions');
    expect(description.value).toContain('document #5, version #9');

    const priority = screen.getByTestId('create-task-priority') as HTMLInputElement;
    expect(priority.value).toBe('High');
  });

  it('resolves the Diligence board scoped to the site', async () => {
    renderDialog();
    await screen.findByTestId('create-task-name');
    expect(mockBoards).toHaveBeenCalledWith('site', 123, { module: 'Diligence' });
  });

  it('creates the task with the lowest-id default status and invalidates tasks', async () => {
    mockCreateTask.mockResolvedValue({ message: 'Task created.', code: 200, entity_id: 42 });
    const onClose = jest.fn();
    renderDialog({ onClose });

    await screen.findByTestId('create-task-name');
    // Submit stays disabled until the statuses query resolves the default status.
    await waitFor(() => expect(screen.getByTestId('create-task-submit')).not.toBeDisabled());
    fireEvent.click(screen.getByTestId('create-task-submit'));

    await waitFor(() => expect(mockCreateTask).toHaveBeenCalledTimes(1));
    const [boardIdArg, payload] = mockCreateTask.mock.calls[0];
    expect(boardIdArg).toBe(77);
    expect(payload).toMatchObject({
      name: 'Diligence: Module Capacity (kW)',
      priority: 'High',
      status_id: 1,
      assignee_id: null
    });
    expect(payload.due_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(mockNotify).toHaveBeenCalledWith('Task created.');
  });

  it('shows a no-board warning and disables submit when there is no Diligence board', async () => {
    mockBoards.mockResolvedValue({ skip: 0, limit: 10, total: 0, items: [] });
    renderDialog();

    await screen.findByTestId('create-task-no-board');
    expect(screen.getByTestId('create-task-submit')).toBeDisabled();
    expect(screen.queryByTestId('create-task-name')).not.toBeInTheDocument();
  });

  it('shows an error state when the board lookup fails', async () => {
    mockBoards.mockRejectedValue({ response: { status: 500 } });
    renderDialog();

    await screen.findByTestId('create-task-board-error');
    expect(screen.getByTestId('create-task-submit')).toBeDisabled();
  });

  it('weaves the project name, document type, and value snapshot into the description', async () => {
    const enrichedRow = {
      ...row,
      source_document_type: 'PPA',
      accepted_value: '120',
      active_fact_value: '125',
      ai_extracted_value: '118'
    } as any;
    renderDialog({ siteName: '110 Shawmut', row: enrichedRow });

    const description = (await screen.findByTestId('create-task-description')) as HTMLTextAreaElement;
    expect(description.value).toContain('Project: 110 Shawmut.');
    expect(description.value).toContain('Document type: PPA.');
    expect(description.value).toContain('Best current value: 125');
    expect(description.value).toContain('Accepted: 120');
    expect(description.value).toContain('Active fact: 125');
    expect(description.value).toContain('AI extracted: 118');
  });

  it('includes provenance IDs, both deep links, and the file-version promotion note', async () => {
    const enrichedRow = {
      ...row,
      document_key_id: 11,
      project_fact_id: 22,
      fact_id: 33,
      ai_run_id: 44
    } as any;
    renderDialog({ siteName: '110 Shawmut', row: enrichedRow });

    const description = (await screen.findByTestId('create-task-description')) as HTMLTextAreaElement;
    expect(description.value).toContain('document #5, version #9');
    expect(description.value).toContain('Document key #11');
    expect(description.value).toContain('Project fact #22');
    expect(description.value).toContain('Active fact id #33');
    expect(description.value).toContain('AI run #44');
    expect(description.value).toContain('/project-hub/projects/123/reconciliation');
    expect(description.value).toContain('/project-hub/projects/123/data-room');
    expect(description.value).toContain('all-or-nothing');
  });
});

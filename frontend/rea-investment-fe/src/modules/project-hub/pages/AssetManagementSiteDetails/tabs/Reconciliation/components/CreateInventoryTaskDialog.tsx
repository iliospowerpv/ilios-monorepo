import React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import Autocomplete from '@mui/material/Autocomplete';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';

import { ApiClient } from '../../../../../../../api';
import type { Assignee } from '../../../../../../../api';
import type { InventoryMismatch, InventoryMismatchTaskResponse } from '../../../../../../../types/telemetryV2';
import { useNotify } from '../../../../../../../contexts/notifications/notifications';

interface CreateInventoryTaskDialogProps {
  open: boolean;
  siteId: number;
  /** The single actionable mismatch this task will track. */
  mismatch: InventoryMismatch;
  /** Project name, woven into the description so the task reads standalone. */
  siteName?: string;
  onClose: () => void;
}

const PRIORITIES = ['Low', 'Medium', 'High'];

/**
 * Mirror of the backend default priority map: a calculation-blocking gap is High,
 * a confidence-lowering gap is Medium, everything else defaults to Medium. The
 * server remains authoritative — this only pre-fills the editable field.
 */
const defaultPriority = (blockingLevel: string | null | undefined): string => {
  if (blockingLevel === 'blocks_calculation') return 'High';
  if (blockingLevel === 'lowers_confidence') return 'Medium';
  return 'Medium';
};

const defaultDueDate = (): string => {
  const date = new Date();
  date.setDate(date.getDate() + 7);
  return date.toISOString().slice(0, 10);
};

const defaultName = (mismatch: InventoryMismatch): string => `Inventory: ${mismatch.title}`.slice(0, 250);

const formatValue = (value: string | null | undefined): string =>
  value === null || value === undefined || value === '' ? '—' : String(value);

/**
 * Provenance-rich, standalone description mirroring the backend default, so the
 * task reads on its own even before anyone opens the reconciliation view again.
 */
const buildDescription = (mismatch: InventoryMismatch, siteName?: string): string => {
  const blocking = mismatch.blocking_level ? String(mismatch.blocking_level).replace(/_/g, ' ') : null;
  const lines: (string | null)[] = [
    siteName ? `Inventory reconciliation follow-up for ${siteName}.` : 'Inventory reconciliation follow-up.',
    `Finding: ${mismatch.title}.`,
    mismatch.detail || null,
    mismatch.category ? `Category: ${mismatch.category}.` : null,
    mismatch.equipment_class ? `Equipment class: ${mismatch.equipment_class}.` : null,
    blocking ? `Impact: ${blocking}.` : null,
    mismatch.recommended_action ? `Recommended action: ${mismatch.recommended_action}` : null,
    mismatch.next_step_target ? `Next step target: ${mismatch.next_step_target}` : null,
    '',
    'Values (read-only snapshot):',
    `• Documented: ${formatValue(mismatch.documented_value)}`,
    `• Observed: ${formatValue(mismatch.observed_value)}`,
    '',
    'Provenance:',
    `• Mismatch signature: ${mismatch.mismatch_signature}`,
    mismatch.device_id != null
      ? `• iliOS device #${mismatch.device_id}${mismatch.device_name ? ` (${mismatch.device_name})` : ''}`
      : null,
    mismatch.external_device_id ? `• External device id: ${mismatch.external_device_id}` : null,
    '',
    'Created from the read-only Inventory Reconciliation view. Reconciliation itself changes nothing — ' +
      'this task only records the work to be done.'
  ];
  return lines.filter((line): line is string => line !== null).join('\n');
};

const assigneeLabel = (assignee: Assignee): string => `${assignee.first_name} ${assignee.last_name}`.trim();

export const CreateInventoryTaskDialog: React.FC<CreateInventoryTaskDialogProps> = ({
  open,
  siteId,
  mismatch,
  siteName,
  onClose
}) => {
  const notify = useNotify();
  const queryClient = useQueryClient();

  const [name, setName] = React.useState('');
  const [description, setDescription] = React.useState('');
  const [priority, setPriority] = React.useState('Medium');
  const [dueDate, setDueDate] = React.useState('');
  const [assignee, setAssignee] = React.useState<Assignee | null>(null);

  // Reset the form to mismatch-derived defaults each time the dialog opens.
  React.useEffect(() => {
    if (open) {
      setName(defaultName(mismatch));
      setDescription(buildDescription(mismatch, siteName));
      setPriority(defaultPriority(mismatch.blocking_level));
      setDueDate(defaultDueDate());
      setAssignee(null);
    }
  }, [open, mismatch, siteName]);

  // Resolve the site's Asset board only to populate the optional assignee picker.
  // The backend independently resolves the Asset board when creating the task.
  const { data: boardsData } = useQuery({
    queryKey: ['task-boards', 'resolve', { scope: 'site', siteId, module: 'Asset' }],
    queryFn: () => ApiClient.taskManagement.boards('site', siteId, { module: 'Asset' }),
    enabled: open,
    retry: false as const
  });

  const boardId = boardsData?.items?.[0]?.id;

  const { data: assigneesData } = useQuery({
    queryKey: ['task-boards', 'assignees', boardId],
    queryFn: () => ApiClient.taskManagement.potentialTaskAssignees(boardId as number, { search: '' }),
    enabled: open && typeof boardId === 'number',
    retry: false as const
  });

  const createTask = useMutation({
    mutationFn: (): Promise<InventoryMismatchTaskResponse> =>
      ApiClient.telemetryV2.createInventoryReconciliationTask(siteId, {
        mismatch_signature: mismatch.mismatch_signature,
        name: name.trim() || null,
        description: description.trim() ? description.trim() : null,
        priority,
        due_date: dueDate || null,
        assignee_id: assignee?.id ?? null
      }),
    onSuccess: result => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['site', 'inventory-reconciliation'] });
      notify(
        result.duplicate ? 'An open task is already tracking this inventory gap.' : result.message || 'Task created.'
      );
      onClose();
    },
    onError: (error: { response?: { data?: { detail?: string; message?: string } } }) => {
      notify(
        error?.response?.data?.detail ||
          error?.response?.data?.message ||
          'Something went wrong while creating the task.'
      );
    }
  });

  const submitDisabled = !name.trim() || createTask.isPending;

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm" data-testid="create-inventory-task-dialog">
      <DialogTitle sx={{ fontWeight: 600 }}>Create a tracked task</DialogTitle>
      <DialogContent dividers>
        <DialogContentText sx={{ mb: 2 }}>
          Track this inventory finding — <strong>{mismatch.title}</strong> — as an Asset management task. This does not
          map, acknowledge, or change any inventory; it only records the work to be done.
        </DialogContentText>

        {mismatch.recommended_action ? (
          <Alert severity="info" sx={{ mb: 2 }} data-testid="create-inventory-task-recommended">
            Recommended action: {mismatch.recommended_action}
          </Alert>
        ) : null}

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <TextField
            label="Task name"
            value={name}
            onChange={event => setName(event.target.value)}
            fullWidth
            required
            inputProps={{ maxLength: 250, 'data-testid': 'create-inventory-task-name' }}
          />
          <TextField
            select
            label="Priority"
            value={priority}
            onChange={event => setPriority(event.target.value)}
            fullWidth
            inputProps={{ 'data-testid': 'create-inventory-task-priority' }}
          >
            {PRIORITIES.map(option => (
              <MenuItem key={option} value={option}>
                {option}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Due date"
            type="date"
            value={dueDate}
            onChange={event => setDueDate(event.target.value)}
            fullWidth
            InputLabelProps={{ shrink: true }}
            inputProps={{ 'data-testid': 'create-inventory-task-due-date' }}
          />
          <Autocomplete
            options={assigneesData?.items ?? []}
            getOptionLabel={assigneeLabel}
            isOptionEqualToValue={(option, value) => option.id === value.id}
            value={assignee}
            onChange={(_event, value) => setAssignee(value)}
            renderInput={params => (
              <TextField
                {...params}
                label="Assignee (optional)"
                inputProps={{ ...params.inputProps, 'data-testid': 'create-inventory-task-assignee' }}
              />
            )}
          />
          <TextField
            label="Description"
            value={description}
            onChange={event => setDescription(event.target.value)}
            fullWidth
            multiline
            minRows={4}
            maxRows={12}
            inputProps={{ 'data-testid': 'create-inventory-task-description' }}
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button
          variant="outlined"
          onClick={onClose}
          disabled={createTask.isPending}
          data-testid="create-inventory-task-cancel"
        >
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={() => createTask.mutate()}
          disabled={submitDisabled}
          data-testid="create-inventory-task-submit"
        >
          {createTask.isPending ? 'Creating…' : 'Create task'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default CreateInventoryTaskDialog;

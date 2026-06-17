import React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Autocomplete from '@mui/material/Autocomplete';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';

import { ApiClient } from '../../../../../../../api';
import type { Assignee, ReconciliationRow } from '../../../../../../../api';
import { useNotify } from '../../../../../../../contexts/notifications/notifications';
import { statusMeta } from '../utils';

interface CreateActionTaskDialogProps {
  open: boolean;
  siteId: number;
  row: ReconciliationRow;
  onClose: () => void;
}

const PRIORITIES = ['Low', 'Medium', 'High'];

const defaultPriority = (blockingLevel: string | null): string => {
  if (blockingLevel === 'blocks_baseline' || blockingLevel === 'blocks_expected' || blockingLevel === 'blocks_reporting') {
    return 'High';
  }
  if (blockingLevel === 'lowers_confidence') return 'Medium';
  if (blockingLevel === 'informational') return 'Low';
  return 'Medium';
};

const defaultDueDate = (): string => {
  const date = new Date();
  date.setDate(date.getDate() + 7);
  return date.toISOString().slice(0, 10);
};

const defaultName = (row: ReconciliationRow): string => `Diligence: ${row.display_label}`.slice(0, 250);

const buildDescription = (row: ReconciliationRow): string => {
  const lines: (string | null)[] = [
    `Reconciliation follow-up for "${row.display_label}" (${row.canonical_field}).`,
    row.required_action ? `Next step: ${row.required_action}` : null,
    `Current status: ${row.status_label || statusMeta(row.status).label}.`,
    row.blocking_level ? `Impact: ${row.blocking_level.replace(/_/g, ' ')}.` : null,
    'Action this from the project Reconciliation tab / Data Room — there is no direct document link on the task.',
    row.document_id != null && row.document_version_id != null
      ? `Source provenance — document #${row.document_id}, version #${row.document_version_id}.`
      : null
  ];
  return lines.filter((line): line is string => Boolean(line)).join('\n');
};

const assigneeLabel = (assignee: Assignee): string => `${assignee.first_name} ${assignee.last_name}`.trim();

export const CreateActionTaskDialog: React.FC<CreateActionTaskDialogProps> = ({ open, siteId, row, onClose }) => {
  const notify = useNotify();
  const queryClient = useQueryClient();

  const [name, setName] = React.useState('');
  const [description, setDescription] = React.useState('');
  const [priority, setPriority] = React.useState('Medium');
  const [dueDate, setDueDate] = React.useState('');
  const [assignee, setAssignee] = React.useState<Assignee | null>(null);

  // Reset the form to row-derived defaults each time the dialog opens.
  React.useEffect(() => {
    if (open) {
      setName(defaultName(row));
      setDescription(buildDescription(row));
      setPriority(defaultPriority(row.blocking_level));
      setDueDate(defaultDueDate());
      setAssignee(null);
    }
  }, [open, row]);

  const {
    data: boardsData,
    isLoading: isBoardsLoading,
    isError: isBoardsError
  } = useQuery({
    queryKey: ['task-boards', 'resolve', { scope: 'site', siteId, module: 'Diligence' }],
    queryFn: () => ApiClient.taskManagement.boards('site', siteId, { module: 'Diligence' }),
    enabled: open,
    retry: false as const
  });

  const board = boardsData?.items?.[0];
  const boardId = board?.id;

  const { data: statusesData, isLoading: isStatusesLoading } = useQuery({
    queryKey: ['task-boards', 'statuses', boardId],
    queryFn: () => ApiClient.taskManagement.getStatuses(boardId as number),
    enabled: open && typeof boardId === 'number',
    retry: false as const
  });

  const { data: assigneesData } = useQuery({
    queryKey: ['task-boards', 'assignees', boardId],
    queryFn: () => ApiClient.taskManagement.potentialTaskAssignees(boardId as number, { search: '' }),
    enabled: open && typeof boardId === 'number',
    retry: false as const
  });

  const defaultStatusId = React.useMemo(() => {
    const statuses = statusesData?.items ? [...statusesData.items] : [];
    statuses.sort((a, b) => a.id - b.id);
    return statuses[0]?.id;
  }, [statusesData]);

  const createTask = useMutation({
    mutationFn: () =>
      ApiClient.taskManagement.createTask(boardId as number, {
        name: name.trim(),
        description: description.trim() ? description.trim() : null,
        priority,
        due_date: dueDate || null,
        assignee_id: assignee?.id ?? null,
        status_id: defaultStatusId as number
      }),
    onSuccess: result => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      notify(result.message || 'Task created.');
      onClose();
    },
    onError: (error: { response?: { data?: { message?: string } } }) => {
      notify(error?.response?.data?.message || 'Something went wrong while creating the task.');
    }
  });

  const noBoard = open && !isBoardsLoading && !isBoardsError && !board;
  const submitDisabled =
    isBoardsLoading ||
    isBoardsError ||
    !board ||
    isStatusesLoading ||
    typeof defaultStatusId !== 'number' ||
    !name.trim() ||
    createTask.isPending;

  const assigneeOptions = assigneesData?.items ?? [];

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm" data-testid="create-task-dialog">
      <DialogTitle sx={{ fontWeight: 600 }}>Create a follow-up task</DialogTitle>
      <DialogContent dividers>
        <DialogContentText sx={{ mb: 2 }}>
          Track the next step for <strong>{row.display_label}</strong> as a Diligence task. This does not change any
          assumption — it only records the work to be done.
        </DialogContentText>

        {isBoardsLoading && (
          <Box display="flex" alignItems="center" justifyContent="center" py={3} data-testid="create-task-loading">
            <CircularProgress size={28} />
          </Box>
        )}

        {isBoardsError && (
          <Alert severity="error" data-testid="create-task-board-error">
            <AlertTitle>Couldn&apos;t load the task board</AlertTitle>
            We couldn&apos;t load the Diligence task board for this project. Please try again later.
          </Alert>
        )}

        {noBoard && (
          <Alert severity="warning" data-testid="create-task-no-board">
            <AlertTitle>No Diligence task board</AlertTitle>
            This project doesn&apos;t have a Diligence task board yet, so a task can&apos;t be created here.
          </Alert>
        )}

        {board && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="Task name"
              value={name}
              onChange={event => setName(event.target.value)}
              fullWidth
              required
              inputProps={{ maxLength: 250, 'data-testid': 'create-task-name' }}
            />
            <TextField
              select
              label="Priority"
              value={priority}
              onChange={event => setPriority(event.target.value)}
              fullWidth
              inputProps={{ 'data-testid': 'create-task-priority' }}
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
              inputProps={{ 'data-testid': 'create-task-due-date' }}
            />
            <Autocomplete
              options={assigneeOptions}
              getOptionLabel={assigneeLabel}
              isOptionEqualToValue={(option, value) => option.id === value.id}
              value={assignee}
              onChange={(_event, value) => setAssignee(value)}
              renderInput={params => (
                <TextField
                  {...params}
                  label="Assignee (optional)"
                  inputProps={{ ...params.inputProps, 'data-testid': 'create-task-assignee' }}
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
              maxRows={10}
              inputProps={{ 'data-testid': 'create-task-description' }}
            />
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button variant="outlined" onClick={onClose} disabled={createTask.isPending} data-testid="create-task-cancel">
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={() => createTask.mutate()}
          disabled={submitDisabled}
          data-testid="create-task-submit"
        >
          {createTask.isPending ? 'Creating…' : 'Create task'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default CreateActionTaskDialog;

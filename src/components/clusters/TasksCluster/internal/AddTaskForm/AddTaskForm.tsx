import * as React from 'react';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { useNavigate } from 'react-router-dom';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import dayjs, { Dayjs } from 'dayjs';
import CustomParseFormatPlugin from 'dayjs/plugin/customParseFormat';

import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContentText from '@mui/material/DialogContentText';
import TextField from '@mui/material/TextField';
import Collapse from '@mui/material/Collapse';
import InputAdornment from '@mui/material/InputAdornment';
import HourglassBottomRoundedIcon from '@mui/icons-material/HourglassBottomRounded';

import { useNotify } from '../../../../../contexts/notifications/notifications';
import { ApiClient } from '../../../../../api';
import { boardQuery } from '../../TasksCluster';

dayjs.extend(CustomParseFormatPlugin);

type CreateTaskParams = Parameters<typeof ApiClient.taskManagement.createTask>[1];

interface AddTaskFormCommonProps {
  boardId?: number;
  companyId: number;
  open: boolean;
  onClose: () => void;
  description?: string;
  alertSeverity?: null | string;
  module?: string;
  alertId?: number | null;
}

type AddTaskFormSiteScopeProps = AddTaskFormCommonProps & {
  scope: 'site';
  siteId: number;
};

type AddTaskFormCompanyScopeProps = AddTaskFormCommonProps & {
  scope: 'company';
  siteId?: undefined;
};

type AddTaskFormProps = AddTaskFormSiteScopeProps | AddTaskFormCompanyScopeProps;

type TaskFormFields = {
  name: string;
  description: null | string;
  priority: string;
  alertSeverity: null | string;
  due_date: Dayjs | null;
  assignee_id: null;
};

export const AddTaskForm: React.FC<AddTaskFormProps> = ({
  scope,
  boardId,
  siteId,
  companyId,
  open,
  onClose,
  description,
  module,
  alertId,
  alertSeverity
}) => {
  const notify = useNotify();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const entityType = scope;
  const entityId = scope === 'company' ? companyId : siteId;
  const shouldUseExternalBoardId = typeof boardId === 'number';
  const shouldResolveBoardByEntityId = open && !shouldUseExternalBoardId;

  const {
    data: taskBoards,
    isLoading: isLoadingTaskBoards,
    error: errorLoadingTaskBoards
  } = useQuery(boardQuery(entityType, entityId, shouldResolveBoardByEntityId, false, module ?? ''));

  const [resolvedBoard] = taskBoards?.items ?? [];
  const resolvedBoardId: number = resolvedBoard ? (resolvedBoard.id as unknown as number) : -1;

  const { mutateAsync: createTask } = useMutation({
    mutationFn: (attributes: CreateTaskParams) =>
      ApiClient.taskManagement.createTask(shouldUseExternalBoardId ? boardId : resolvedBoardId, attributes)
  });

  const {
    data: statusesResponseData,
    isLoading: isLoadingStatuses,
    error: statusesLoadingError
  } = useQuery({
    queryFn: () => ApiClient.taskManagement.getStatuses(shouldUseExternalBoardId ? boardId : resolvedBoardId),
    queryKey: ['task-boards', 'statuses', boardId],
    enabled: open && (shouldUseExternalBoardId || !!resolvedBoard)
  });

  const { handleSubmit, formState, control, reset } = useForm<TaskFormFields>({
    mode: 'all',
    criteriaMode: 'all',
    reValidateMode: 'onChange',
    defaultValues: {
      name: undefined,
      description: null,
      priority: 'Medium',
      due_date: undefined,
      assignee_id: null
    }
  });

  const onSubmit: SubmitHandler<TaskFormFields> = async data => {
    try {
      const statuses = statusesResponseData ? [...statusesResponseData.items] : [];
      const [defaultStatus] = statuses.sort((taskA, taskB) => taskA.id - taskB.id);

      if (!defaultStatus) {
        throw new Error('Cannot find default board status.');
      }
      if (description) {
        data.description = description;
      }

      if (alertSeverity) {
        const severityToPriorityMap: Record<'Critical' | 'Warning' | 'Informational', string> = {
          Critical: 'High',
          Warning: 'Medium',
          Informational: 'Low'
        };

        data.priority = severityToPriorityMap[alertSeverity as 'Critical' | 'Warning' | 'Informational'] || 'Medium';
      }

      const { message, entity_id: taskId } = await createTask({
        ...data,
        status_id: defaultStatus.id,
        due_date: data.due_date ? data.due_date.format('YYYY-MM-DD') : null,
        ...(typeof alertId === 'number' && { alert_id: alertId })
      });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      notify(message || `Task was successfully created.`);
      reset();
      notify('Redirecting...');
      setTimeout(() => {
        if (description || module === 'O&M') {
          if (scope === 'site') {
            navigate(
              `/operations-and-maintenance/companies/${companyId}/sites/${siteId}/tasks/${taskId}?editOnLanding=true`
            );
            return;
          }
          navigate(`/operations-and-maintenance/companies/${companyId}/tasks/${taskId}?editOnLanding=true`);
          return;
        }
        if (scope === 'site') {
          navigate(`/asset-management/companies/${companyId}/sites/${siteId}/tasks/${taskId}?editOnLanding=true`);
          return;
        }
        navigate(`/asset-management/companies/${companyId}/tasks/${taskId}?editOnLanding=true`);
      }, 1000);
    } catch (e: any) {
      notify(e.response?.data?.message || 'Something went wrong when creating a task...');
    }
  };

  const handleCancelClick = () => {
    reset();
    onClose();
  };

  const handleClose = (event: object, reason: 'backdropClick' | 'escapeKeyDown'): void => {
    if (reason === 'escapeKeyDown' && !isSubmitting) onClose();
  };

  const { errors, isValid, isSubmitting, isDirty } = formState;

  return (
    <Dialog
      fullWidth
      maxWidth="sm"
      open={open}
      onClose={handleClose}
      PaperProps={{
        component: 'form',
        onSubmit: handleSubmit(onSubmit)
      }}
    >
      <DialogTitle sx={{ bgcolor: 'primary.main', color: 'secondary.main' }}>Add a New Task</DialogTitle>
      <DialogContent sx={{ padding: '18px !important', position: 'relative' }}>
        <DialogContentText sx={{ paddingBottom: '12px' }}>
          Please enter the task name and indicate the due date.
        </DialogContentText>
        <Controller
          name="name"
          control={control}
          rules={{
            required: 'Task Name is required field.',
            maxLength: {
              value: 250,
              message: 'Task Name length should not exceed 250 characters.'
            }
          }}
          render={({ field: { ref, value, ...field } }) => (
            <TextField
              {...field}
              multiline
              minRows={1}
              maxRows={3}
              fullWidth
              variant="standard"
              required
              disabled={isLoadingStatuses || isLoadingTaskBoards}
              id="task-name"
              label="Task Name"
              helperText={errors.name?.message}
              error={!!errors.name}
              inputRef={ref}
              value={value || ''}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    {isLoadingStatuses || isLoadingTaskBoards ? <HourglassBottomRoundedIcon /> : null}
                  </InputAdornment>
                )
              }}
            />
          )}
        />
        <Controller
          name="due_date"
          control={control}
          rules={{
            validate: value => {
              if (!value) return 'Due Date is required field.';
              if (!dayjs(value).isValid()) return 'Please enter correct Due Date.';
              return (
                value.isAfter(dayjs().subtract(1, 'day').endOf('day')) ||
                'Due Date cannot be earlier than the current date.'
              );
            }
          }}
          render={({ field: { ref, value, onChange, onBlur, ...field } }) => (
            <DatePicker
              {...field}
              value={value ?? null}
              format="MM/DD/YYYY"
              inputRef={ref}
              onChange={val => onChange(val)}
              disablePast
              slotProps={{
                textField: {
                  onBlur,
                  required: true,
                  disabled: isLoadingStatuses || isLoadingTaskBoards,
                  id: 'task-due-date',
                  label: 'Due Date',
                  error: !!errors.due_date,
                  helperText: errors.due_date?.message,
                  fullWidth: true,
                  variant: 'standard',
                  sx: { mt: '8px' },
                  InputProps: {
                    ...((isLoadingStatuses || isLoadingTaskBoards) && {
                      endAdornment: (
                        <InputAdornment position="end">
                          <HourglassBottomRoundedIcon />
                        </InputAdornment>
                      )
                    })
                  }
                }
              }}
            />
          )}
        />
        {statusesLoadingError && !isLoadingStatuses && (
          <Collapse in={!!statusesLoadingError} sx={{ paddingTop: '12px' }}>
            <Alert severity="error">
              An error occured when retrieving board statuses:&nbsp;
              {statusesLoadingError instanceof AxiosError
                ? statusesLoadingError.response?.data?.message
                : statusesLoadingError?.message}
            </Alert>
          </Collapse>
        )}
        {errorLoadingTaskBoards && !isLoadingTaskBoards && (
          <Collapse in={!!errorLoadingTaskBoards} sx={{ paddingTop: '12px' }}>
            <Alert severity="error">
              An error occured when resolving the board for this {scope}:&nbsp;
              {errorLoadingTaskBoards instanceof AxiosError
                ? errorLoadingTaskBoards.response?.data?.message
                : errorLoadingTaskBoards?.message}
            </Alert>
          </Collapse>
        )}
      </DialogContent>
      <DialogActions>
        <Button sx={{ width: '80px' }} variant="outlined" onClick={handleCancelClick} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button
          sx={{ width: '80px' }}
          variant="contained"
          disabled={!isValid || !isDirty || isSubmitting || isLoadingStatuses || !!statusesLoadingError}
          type="submit"
        >
          Add
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default AddTaskForm;

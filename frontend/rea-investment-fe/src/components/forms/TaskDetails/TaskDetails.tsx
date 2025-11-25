import React from 'react';
import dayjs, { Dayjs } from 'dayjs';
import { AxiosError } from 'axios';
import CustomParseFormatPlugin from 'dayjs/plugin/customParseFormat';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
import { useTheme } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import IconButton from '@mui/material/IconButton';
import EditIcon from '@mui/icons-material/Edit';
import Zoom from '@mui/material/Zoom';
import TextField from '@mui/material/TextField';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Fade from '@mui/material/Fade';
import Avatar from '@mui/material/Avatar';
import HourglassBottomRounded from '@mui/icons-material/HourglassBottomRounded';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import PersonIcon from '@mui/icons-material/Person';
import FlagIcon from '@mui/icons-material/Flag';

import { useNotify } from '../../../contexts/notifications/notifications';
import { ApiClient } from '../../../api';

import AssigneeSearchField from '../AssigneeSearchField/AssigneeSearchField';
import DeviceSearchField from '../DeviceSearchField/DeviceSearchField';
import { FieldCell, StyledSelectItem, TextBox, DetailsContainer } from './TaskDetails.styles';
import FormHelperText from '@mui/material/FormHelperText';
import WarningRoundedIcon from '@mui/icons-material/WarningRounded';

dayjs.extend(CustomParseFormatPlugin);

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

type UpdateTask = typeof ApiClient.taskManagement.updateTask;
type UpdateTaskAttributes = Parameters<UpdateTask>[2];
type TaskByIdQuery = typeof ApiClient.taskManagement.getTaskById;
type TaskData = Omit<Awaited<ReturnType<TaskByIdQuery>>, 'description'>;
type TaskUser = Exclude<TaskData['assignee'], null>;
type TaskDevice = Exclude<TaskData['affected_device'], null>;

interface TaskFormFields {
  assignee: TaskUser | null;
  due_date: Dayjs | null;
  priority: 'Low' | 'Medium' | 'High';
  name: string;
  status_id: number;
  affected_device: TaskDevice | null;
}

interface TaskDetailsCommonProps {
  boardId: number;
  initialMode?: 'view' | 'edit';
}

type TaskDetailsSiteScopeProps = TaskDetailsCommonProps & {
  taskData: TaskData;
  scope: 'site';
  siteName: string;
  siteId: number;
  module?: string;
};

type TaskDetailsCompanyScopeProps = TaskDetailsCommonProps & {
  taskData: TaskData;
  scope: 'company';
  siteName?: undefined;
  siteId?: undefined;
  module?: string;
};

type DiligenceDocumentTaskData = Omit<TaskData, 'external_id' | 'creator' | 'affected_device'>;

type TaskDetailsDiligenceScopeProps = TaskDetailsCommonProps & {
  taskData: DiligenceDocumentTaskData;
  scope: 'diligence';
  siteName?: undefined;
  siteId?: undefined;
  module?: string;
};

export const TaskDetails: React.FC<
  TaskDetailsSiteScopeProps | TaskDetailsCompanyScopeProps | TaskDetailsDiligenceScopeProps
> = ({ siteName, taskData, boardId, initialMode, scope, siteId, module }) => {
  const [mode, setMode] = React.useState<'view' | 'edit'>(initialMode ?? 'view');

  const { efficiencyColors, color } = useTheme();
  const queryClient = useQueryClient();
  const notify = useNotify();

  const priorityColorMapping: Readonly<{ [key in 'Low' | 'Medium' | 'High']: string }> = Object.freeze({
    Low: efficiencyColors.good,
    Medium: efficiencyColors.mediocre,
    High: efficiencyColors.low
  });

  const { mutateAsync: updateTaskDetails } = useMutation({
    mutationFn: (args: UpdateTaskAttributes) => ApiClient.taskManagement.updateTask(boardId, taskData.id, args)
  });

  const { mutateAsync: resolveAlert } = useMutation({
    mutationFn: (alert_id: number) => ApiClient.operationsAndMaintenance.companyAlertResolve(alert_id)
  });

  const {
    data: statusesResponseData,
    isFetching: isFetchingStatuses,
    error: statusesLoadingError
  } = useQuery({
    queryFn: () => ApiClient.taskManagement.getStatuses(boardId),
    queryKey: ['task-boards', 'statuses', boardId],
    initialData: taskData.status ? { items: [taskData.status] } : undefined
  });

  const { handleSubmit, formState, control, reset, watch } = useForm<TaskFormFields>({
    mode: 'all',
    criteriaMode: 'all',
    reValidateMode: 'onChange',
    defaultValues: {
      assignee: taskData.assignee,
      due_date: taskData.due_date ? dayjs(taskData.due_date, 'YYYY-MM-DD', true) : null,
      priority: taskData.priority,
      name: taskData.name,
      status_id: taskData.status.id,
      affected_device: scope !== 'diligence' ? taskData.affected_device : null
    }
  });

  const selectedValue = watch('status_id');
  const isSelected = statusesResponseData?.items?.some(
    item =>
      (item.name === 'Closed' || item.name === 'Cancelled') &&
      item.id === selectedValue &&
      formState.dirtyFields.status_id
  );
  const { errors, isValid, isSubmitting, isDirty, dirtyFields } = formState;

  React.useEffect(() => {
    reset({
      assignee: taskData.assignee,
      affected_device: scope !== 'diligence' ? taskData.affected_device : null,
      due_date: taskData.due_date ? dayjs(taskData.due_date, 'YYYY-MM-DD', true) : null,
      priority: taskData.priority,
      name: taskData.name,
      status_id: taskData.status.id
    });
  }, [taskData, reset, scope]);

  const onSubmit: SubmitHandler<TaskFormFields> = async data => {
    try {
      const response = await updateTaskDetails({
        name: data.name,
        status_id: data.status_id,
        due_date: data.due_date ? data.due_date.format('YYYY-MM-DD') : null,
        assignee_id: data.assignee ? data.assignee.id : null,
        affected_device_id: data.affected_device ? data.affected_device.id : null,
        priority: data.priority
      });
      if (taskData.alert_id && module === 'O&M' && isSelected) {
        const response = await resolveAlert(taskData.alert_id);
        notify(response.message || `Alert was successfully resolve.`);
      }
      notify(response.message || `Task details were successfully updated.`);
      reset({
        assignee: data.assignee,
        due_date: data.due_date,
        priority: data.priority,
        name: data.name,
        status_id: data.status_id,
        affected_device: data.affected_device
      });
      queryClient.invalidateQueries({ queryKey: scope === 'diligence' ? ['documents'] : ['tasks'] });
      mode === 'edit' && setMode('view');
    } catch (e: any) {
      notify(e.response?.data?.message || 'Something went wrong when updating the task details...');
    }
  };

  const handleClickEdit = () => setMode('edit');

  const handleClickCancel = () => {
    reset();
    setMode('view');
  };

  const { creator, name, status, assignee, priority, due_date, affected_device } =
    scope !== 'diligence' ? taskData : { ...taskData, creator: null, affected_device: null };

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)}>
      {scope !== 'diligence' && (
        <Typography variant="h6" fontSize="16px" mb="12px" fontWeight="600">
          Details
        </Typography>
      )}
      <DetailsContainer position="relative" display="flex" flexDirection="column" flexGrow={1}>
        <Table sx={{ width: '100%', height: 'auto', tableLayout: 'fixed' }} size="small">
          <TableBody>
            {scope !== 'diligence' && (
              <TableRow>
                <FieldCell
                  sx={{ paddingTop: mode === 'edit' ? '16px' : '8px' }}
                  component="th"
                  scope="row"
                  width="120px"
                >
                  <TextBox fieldName>Task Name</TextBox>
                </FieldCell>
                <FieldCell component="th" scope="row" align="left">
                  {mode === 'view' ? (
                    <TextBox>{name}</TextBox>
                  ) : (
                    <Controller
                      name="name"
                      control={control}
                      rules={{
                        required: 'Task Name is required field',
                        maxLength: {
                          value: 250,
                          message: 'Task Name length should not exceed the limit of 250 characters.'
                        }
                      }}
                      render={({ field: { ref, value, onChange, ...field } }) => (
                        <TextField
                          {...field}
                          fullWidth
                          size="small"
                          placeholder="Add Task Name…"
                          error={!!errors.name}
                          helperText={errors.name?.message}
                          multiline
                          minRows={1}
                          maxRows={3}
                          disabled={isSubmitting}
                          inputRef={ref}
                          value={value || ''}
                          onChange={e => onChange(e.target.value || null)}
                          variant="outlined"
                          InputProps={{ sx: inputStyles }}
                        />
                      )}
                    />
                  )}
                </FieldCell>
              </TableRow>
            )}
            {scope === 'site' && (
              <TableRow>
                <FieldCell component="th" scope="row" width="100px">
                  <TextBox fieldName>Site</TextBox>
                </FieldCell>
                <FieldCell component="th" scope="row" align="left">
                  <TextBox>{siteName}</TextBox>
                </FieldCell>
              </TableRow>
            )}
            {scope === 'site' && (
              <TableRow>
                <FieldCell
                  sx={{ paddingTop: mode === 'edit' ? '16px' : '8px' }}
                  component="th"
                  scope="row"
                  width="120px"
                >
                  <TextBox fieldName>Affected Device</TextBox>
                </FieldCell>
                <FieldCell component="th" scope="row" align="left">
                  {mode === 'view' ? (
                    <TextBox>{affected_device ? affected_device.name : 'None'}</TextBox>
                  ) : (
                    <Controller
                      name="affected_device"
                      control={control}
                      render={({ field: { ref, value, onChange, ...field } }) => (
                        <DeviceSearchField
                          {...field}
                          siteId={siteId}
                          value={value}
                          onChange={(evt, value) => onChange(value)}
                          ref={ref}
                          inputStyleOverrides={inputStyles}
                        />
                      )}
                    />
                  )}
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell sx={{ paddingTop: mode === 'edit' ? '16px' : '8px' }} component="th" scope="row" width="120px">
                <TextBox fieldName>Status</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="left">
                {mode === 'view' ? (
                  <TextBox>{status.name}</TextBox>
                ) : (
                  <Controller
                    name="status_id"
                    control={control}
                    rules={{
                      required: 'Status is required field'
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting || isFetchingStatuses}
                        placeholder="Set task Status…"
                        error={!!errors.status_id || !!statusesLoadingError}
                        helperText={
                          errors.status_id?.message ||
                          (statusesLoadingError instanceof AxiosError
                            ? statusesLoadingError.response?.data.message
                            : statusesLoadingError?.message)
                        }
                        SelectProps={{ IconComponent: isFetchingStatuses ? HourglassBottomRounded : undefined }}
                        InputProps={{
                          sx: inputStyles
                        }}
                        select
                        fullWidth
                        variant="outlined"
                        size="small"
                      >
                        {statusesResponseData &&
                          statusesResponseData.items.map(status => (
                            <StyledSelectItem key={status.id} value={status.id}>
                              {status.name}
                            </StyledSelectItem>
                          ))}
                      </TextField>
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell sx={{ paddingTop: mode === 'edit' ? '16px' : '8px' }} component="th" scope="row" width="120px">
                <TextBox fieldName>Due Date</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="left">
                {mode === 'view' ? (
                  <TextBox>{due_date ? dayjs(due_date, 'YYYY-MM-DD', true).format('MM/DD/YYYY') : 'None'}</TextBox>
                ) : (
                  <Controller
                    name="due_date"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return 'Due Date is required field.';
                        if (!dayjs(value).isValid()) return 'Please enter correct Due Date.';
                        if (!dirtyFields?.due_date) return true;
                        return (
                          value.isAfter(dayjs().subtract(1, 'day').endOf('day')) ||
                          'Due Date cannot be earlier than the current date.'
                        );
                      }
                    }}
                    render={({ field: { ref, value, onChange, onBlur, ...field } }) => (
                      <DatePicker
                        {...field}
                        value={value}
                        format="MM/DD/YYYY"
                        inputRef={ref}
                        onChange={val => onChange(val)}
                        disablePast
                        slotProps={{
                          textField: {
                            onBlur,
                            required: true,
                            disabled: isSubmitting,
                            error: !!errors.due_date,
                            helperText: errors.due_date?.message,
                            size: 'small',
                            fullWidth: true,
                            InputProps: { sx: inputStyles },
                            variant: 'outlined'
                          }
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell sx={{ paddingTop: mode === 'edit' ? '16px' : '8px' }} component="th" scope="row" width="120px">
                <TextBox fieldName>Assigned to</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="left">
                {mode === 'view' ? (
                  <Box display="inline-flex" alignItems="center">
                    <Avatar
                      sx={{
                        width: '25px',
                        height: '25px',
                        fontSize: '12px',
                        fontWeight: '600',
                        backgroundColor: color.blueGray,
                        lineHeight: '25px',
                        display: 'inline-flex',
                        mr: '6px'
                      }}
                    >
                      {assignee ? (
                        `${assignee.first_name.charAt(0)}${assignee.last_name.charAt(0)}`
                      ) : (
                        <PersonIcon fontSize="small" />
                      )}
                    </Avatar>
                    <TextBox>{assignee ? `${assignee.first_name} ${assignee.last_name}` : 'None'}</TextBox>
                  </Box>
                ) : (
                  <Controller
                    name="assignee"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <AssigneeSearchField
                        {...field}
                        boardId={boardId}
                        value={value}
                        onChange={(evt, value) => onChange(value)}
                        ref={ref}
                        inputStyleOverrides={inputStyles}
                        taskId={taskData?.id}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell sx={{ paddingTop: mode === 'edit' ? '16px' : '8px' }} component="th" scope="row" width="120px">
                <TextBox fieldName>Priority</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="left">
                {mode === 'view' ? (
                  <Box display="inline-flex" alignItems="center">
                    <FlagIcon fontSize="small" sx={{ mr: '4px', color: priorityColorMapping[priority] }} />
                    <TextBox>{priority}</TextBox>
                  </Box>
                ) : (
                  <Controller
                    name="priority"
                    control={control}
                    rules={{
                      required: 'Priority is required field'
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        placeholder="Set task priority…"
                        error={!!errors.priority}
                        helperText={errors.priority?.message}
                        InputProps={{
                          sx: inputStyles
                        }}
                        select
                        fullWidth
                        variant="outlined"
                        size="small"
                      >
                        <StyledSelectItem value="Low">Low</StyledSelectItem>
                        <StyledSelectItem value="Medium">Medium</StyledSelectItem>
                        <StyledSelectItem value="High">High</StyledSelectItem>
                      </TextField>
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            {scope !== 'diligence' && creator && (
              <TableRow>
                <FieldCell component="th" scope="row" width="120px">
                  <TextBox fieldName>Created by</TextBox>
                </FieldCell>
                <FieldCell component="th" scope="row" align="left">
                  <TextBox>{`${creator.first_name} ${creator.last_name}`}</TextBox>
                </FieldCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        <TextBox>
          <FormHelperText sx={{ padding: 1, margin: 0 }} error>
            {module === 'O&M' && mode === 'edit' && isSelected && (
              <Box display="flex" alignItems="center">
                <WarningRoundedIcon sx={{ color: theme => theme.alertSeverity.high, marginRight: 1 }} />
                <span>You are about to close this task. Closing this task will also resolve the associated alert.</span>
              </Box>
            )}
          </FormHelperText>
        </TextBox>
        <Zoom in={mode === 'view'}>
          <Box position="absolute" top="8px" right="8px" borderRadius="50%" bgcolor="rgba(255, 255, 255, 0.85)">
            <IconButton data-testid="task_details-details-edit_btn" size="medium" onClick={handleClickEdit}>
              <EditIcon />
            </IconButton>
          </Box>
        </Zoom>
      </DetailsContainer>
      <Fade in={mode === 'edit'} timeout={{ enter: 1000, exit: 1000 }}>
        <Stack direction="row" width="100%" py="10px" spacing={1} justifyContent="flex-end">
          <Button disabled={!isValid || !isDirty || isSubmitting} variant="contained" size="small" type="submit">
            Save
          </Button>
          <Button disabled={isSubmitting} variant="outlined" size="small" onClick={handleClickCancel}>
            Cancel
          </Button>
        </Stack>
      </Fade>
    </Box>
  );
};

export default TaskDetails;

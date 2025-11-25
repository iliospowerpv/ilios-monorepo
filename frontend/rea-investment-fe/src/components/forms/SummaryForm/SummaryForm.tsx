import React from 'react';
import dayjs, { Dayjs } from 'dayjs';
import CustomParseFormatPlugin from 'dayjs/plugin/customParseFormat';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Controller, SubmitHandler, useForm } from 'react-hook-form';
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
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { useNotify } from '../../../contexts/notifications/notifications';
import { ApiClient } from '../../../api';

import { FieldCell, StyledSelectItem, TextBox, DetailsContainer } from './SummaryForm.styles';

dayjs.extend(CustomParseFormatPlugin);

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

type UpdateTask = typeof ApiClient.taskManagement.updateSiteVisit;
type UpdateTaskAttributes = Parameters<UpdateTask>[2];
type TaskByIdQuery = typeof ApiClient.taskManagement.getSiteVisit;
type TaskData = Awaited<ReturnType<TaskByIdQuery>>;

interface TaskFormFields {
  service_date: Dayjs | null;
  technician_assignee: string | null;
  reasons: string | null;
  scope_of_work: string | null;
  status: string | null;
  resolution: string | null;
  next_steps: string | null;
  pending_work: string | null;
  recommendations: string | null;
}

type TaskDetailsSiteScopeProps = {
  taskData: TaskData;
  scope: 'site';
  siteName: string;
  taskId: number;
  boardId: number;
};

export const SummaryForm: React.FC<TaskDetailsSiteScopeProps> = ({ taskData, boardId, scope, taskId }) => {
  const [mode, setMode] = React.useState<'view' | 'edit'>('view');
  const queryClient = useQueryClient();
  const notify = useNotify();

  const { mutateAsync: updateTaskDetails } = useMutation({
    mutationFn: (args: UpdateTaskAttributes) => ApiClient.taskManagement.updateSiteVisit(boardId, taskId, args)
  });

  const { handleSubmit, formState, control, reset } = useForm<TaskFormFields>({
    mode: 'all',
    criteriaMode: 'all',
    reValidateMode: 'onChange',
    defaultValues: {
      service_date: taskData.service_date ? dayjs(taskData.service_date, 'YYYY-MM-DD', true) : null,
      technician_assignee: taskData.technician_assignee,
      reasons: taskData.reasons,
      scope_of_work: taskData.scope_of_work,
      status: taskData.status,
      resolution: taskData.resolution,
      next_steps: taskData.next_steps,
      pending_work: taskData.pending_work,
      recommendations: taskData.recommendations
    }
  });

  const { errors, isValid, isSubmitting, isDirty } = formState;

  React.useEffect(() => {
    reset({
      service_date: taskData.service_date ? dayjs(taskData.service_date, 'YYYY-MM-DD', true) : null,
      technician_assignee: taskData.technician_assignee,
      reasons: taskData.reasons,
      scope_of_work: taskData.scope_of_work,
      status: taskData.status,
      resolution: taskData.resolution,
      next_steps: taskData.next_steps,
      pending_work: taskData.pending_work,
      recommendations: taskData.recommendations
    });
  }, [taskData, reset, scope]);

  const onSubmit: SubmitHandler<TaskFormFields> = async data => {
    try {
      const response = await updateTaskDetails({
        service_date: data.service_date ? data.service_date.format('YYYY-MM-DD') : null,
        technician_assignee: data.technician_assignee ? data.technician_assignee : null,
        reasons: data.reasons ? data.reasons : null,
        scope_of_work: data.scope_of_work ? data.scope_of_work : null,
        status: data.status ? data.status : null,
        resolution: data.resolution ? data.resolution : null,
        next_steps: data.next_steps ? data.next_steps : null,
        pending_work: data.pending_work ? data.pending_work : null,
        recommendations: data.recommendations ? data.recommendations : null
      });
      notify(response.message || `Task details were successfully updated.`);
      reset({
        service_date: data.service_date,
        technician_assignee: data.technician_assignee,
        reasons: data.reasons,
        scope_of_work: data.scope_of_work,
        status: data.status,
        resolution: data.resolution,
        next_steps: data.next_steps,
        pending_work: data.pending_work,
        recommendations: data.recommendations
      });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
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

  const {
    service_date,
    technician_assignee,
    reasons,
    scope_of_work,
    status,
    resolution,
    next_steps,
    pending_work,
    recommendations
  } = taskData;

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)}>
      <Typography variant="h6" fontSize="16px" mb="12px" fontWeight="600">
        Overview
      </Typography>
      <DetailsContainer position="relative" display="flex" flexDirection="column" flexGrow={1}>
        <Table sx={{ width: '100%', height: 'auto', tableLayout: 'fixed' }} size="small">
          <TableBody>
            <TableRow>
              <FieldCell sx={{ paddingTop: mode === 'edit' ? '16px' : '8px' }} component="th" scope="row" width="150px">
                <TextBox fieldName>Service Date</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="left">
                {mode === 'view' ? (
                  <TextBox>
                    {service_date ? dayjs(service_date, 'YYYY-MM-DD', true).format('MM/DD/YYYY') : null}
                  </TextBox>
                ) : (
                  <Controller
                    name="service_date"
                    control={control}
                    rules={{
                      validate: value => {
                        if (!value) return true;
                        return dayjs(value).isValid() || 'Please enter correct Service Date.';
                      }
                    }}
                    render={({ field: { ref, value, onChange, onBlur, ...field } }) => (
                      <DatePicker
                        {...field}
                        value={value}
                        format="MM/DD/YYYY"
                        inputRef={ref}
                        onChange={val => onChange(val)}
                        slotProps={{
                          textField: {
                            onBlur,
                            disabled: isSubmitting,
                            error: !!errors.service_date,
                            helperText: errors.service_date?.message,
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
              <FieldCell sx={{ paddingTop: '8px' }} component="th" scope="row" width="150px">
                <TextBox fieldName>Service Type</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="left">
                <TextBox>Reactive</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="150px">
                <TextBox fieldName>Technician Assigned</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{technician_assignee || ''}</TextBox>
                ) : (
                  <Controller
                    name="technician_assignee"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Technician Assigned length should be less than 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.technician_assignee}
                        helperText={errors.technician_assignee?.message}
                        multiline
                        minRows={1}
                        maxRows={3}
                        inputRef={ref}
                        disabled={isSubmitting}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          sx: inputStyles
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="120px">
                <TextBox fieldName>Reasons for Visit</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{reasons || ''}</TextBox>
                ) : (
                  <Controller
                    name="reasons"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 2000,
                        message: 'Reasons for Visit length should be less than 2000 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.reasons}
                        helperText={errors.reasons?.message}
                        multiline
                        minRows={3}
                        maxRows={3}
                        inputRef={ref}
                        disabled={isSubmitting}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          sx: inputStyles
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="120px">
                <TextBox fieldName>Scope of Work</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{scope_of_work || ''}</TextBox>
                ) : (
                  <Controller
                    name="scope_of_work"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 2000,
                        message: 'Scope of Work length should be less than 2000 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.scope_of_work}
                        helperText={errors.scope_of_work?.message}
                        multiline
                        minRows={3}
                        maxRows={3}
                        inputRef={ref}
                        disabled={isSubmitting}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          sx: inputStyles
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow sx={{ borderTop: '1px solid #0000003B' }}>
              <FieldCell component="th" scope="row" width="150px">
                <TextBox fieldName sx={{ fontSize: '16px' }}>
                  Resolution:
                </TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="150px">
                <TextBox fieldName>Status</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'view' ? 'right' : 'left'}>
                {mode === 'view' ? (
                  <TextBox>{status || ''}</TextBox>
                ) : (
                  <Controller
                    name="status"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.status}
                        helperText={errors.status?.message}
                        InputProps={{
                          sx: inputStyles
                        }}
                        select
                        fullWidth
                        variant="outlined"
                        size="small"
                      >
                        <StyledSelectItem value="Resolved">Resolved</StyledSelectItem>
                        <StyledSelectItem value="Escalated">Escalated</StyledSelectItem>
                        <StyledSelectItem value="RMA">RMA</StyledSelectItem>
                      </TextField>
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="120px">
                <TextBox fieldName>Description</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{resolution || ''}</TextBox>
                ) : (
                  <Controller
                    name="resolution"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 2000,
                        message: 'Description length should be less than 2000 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.resolution}
                        helperText={errors.resolution?.message}
                        multiline
                        minRows={3}
                        maxRows={3}
                        inputRef={ref}
                        disabled={isSubmitting}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          sx: inputStyles
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="120px">
                <TextBox fieldName>Next Steps</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{next_steps || ''}</TextBox>
                ) : (
                  <Controller
                    name="next_steps"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 2000,
                        message: 'Next Steps length should be less than 2000 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.next_steps}
                        helperText={errors.next_steps?.message}
                        multiline
                        minRows={3}
                        maxRows={3}
                        inputRef={ref}
                        disabled={isSubmitting}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          sx: inputStyles
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="120px">
                <TextBox fieldName>Pending Work</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{pending_work || ''}</TextBox>
                ) : (
                  <Controller
                    name="pending_work"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 2000,
                        message: 'Pending Work length should be less than 2000 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.pending_work}
                        helperText={errors.pending_work?.message}
                        multiline
                        minRows={3}
                        maxRows={3}
                        inputRef={ref}
                        disabled={isSubmitting}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          sx: inputStyles
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="120px">
                <TextBox fieldName>Recommendations</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{recommendations || ''}</TextBox>
                ) : (
                  <Controller
                    name="recommendations"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 2000,
                        message: 'Recommendations length should be less than 2000 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.recommendations}
                        helperText={errors.recommendations?.message}
                        multiline
                        minRows={3}
                        maxRows={3}
                        inputRef={ref}
                        disabled={isSubmitting}
                        value={value || ''}
                        onChange={e => onChange(e.target.value || null)}
                        variant="outlined"
                        InputProps={{
                          sx: inputStyles
                        }}
                      />
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
          </TableBody>
        </Table>
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

export default SummaryForm;

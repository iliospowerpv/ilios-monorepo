import React from 'react';
import dayjs from 'dayjs';
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
import Divider from '@mui/material/Divider';
import Fade from '@mui/material/Fade';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';

import { useNotify } from '../../../../../../../../contexts/notifications/notifications';
import { ApiClient } from '../../../../../../../../api';
import { FieldCell, StyledSelectItem, TextBox, DetailsContainer } from './ServiceDetail.styles';
import { ServiceDetailCardFormFields } from '../../../../../../../../api/asset-management';
import FormHelperText from '@mui/material/FormHelperText';

dayjs.extend(CustomParseFormatPlugin);

const inputStyles = { fontSize: '0.875rem', lineHeight: 1.43 };

type UpdateServiceDetail = typeof ApiClient.assetManagement.updateServiceDetail;
type UpdateServiceDetailAttributes = Parameters<UpdateServiceDetail>[2];

interface ServiceDetailProps {
  serviceDetailData: ServiceDetailCardFormFields;
  siteId: number;
  deviceId: number;
  initialMode?: 'view' | 'edit';
}

export const ServiceDetailCard: React.FC<ServiceDetailProps> = ({
  serviceDetailData,
  siteId,
  deviceId,
  initialMode
}) => {
  const [mode, setMode] = React.useState<'view' | 'edit'>(initialMode ?? 'view');

  const queryClient = useQueryClient();
  const notify = useNotify();

  const { mutateAsync: updateServiceDetail } = useMutation({
    mutationFn: (args: UpdateServiceDetailAttributes) =>
      ApiClient.assetManagement.updateServiceDetail(deviceId, siteId, args)
  });

  const { handleSubmit, formState, control, reset } = useForm<ServiceDetailCardFormFields>({
    mode: 'onChange',
    criteriaMode: 'all',
    reValidateMode: 'onChange',
    defaultValues: {
      availability: serviceDetailData.availability,
      failure_rate: serviceDetailData.failure_rate,
      warranty_period: serviceDetailData.warranty_period,
      lifetime: serviceDetailData.lifetime,
      mtbr: serviceDetailData.mtbr,
      mttr: serviceDetailData.mttr,
      next_scheduled_service_date: serviceDetailData.next_scheduled_service_date,
      open_repair_tickets_count: serviceDetailData.open_repair_tickets_count,
      test_interval: serviceDetailData.test_interval
    }
  });

  const { errors, isValid, isSubmitting, isDirty } = formState;

  React.useEffect(() => {
    reset({
      warranty_period: serviceDetailData.warranty_period,
      next_scheduled_service_date: serviceDetailData.next_scheduled_service_date
        ? dayjs(serviceDetailData.next_scheduled_service_date, 'YYYY-MM-DD', true)
        : null,
      lifetime: serviceDetailData.lifetime
    });
  }, [serviceDetailData, reset]);

  const onSubmit: SubmitHandler<ServiceDetailCardFormFields> = async data => {
    try {
      const response = await updateServiceDetail({
        ...(data.warranty_period && { warranty_period: data.warranty_period }),
        ...(data.lifetime && { lifetime: data.lifetime }),
        ...(data.next_scheduled_service_date && {
          next_scheduled_service_date: data.next_scheduled_service_date
            ? data.next_scheduled_service_date.format('YYYY-MM-DD')
            : null
        })
      });
      notify(response.message || `Service details were successfully updated.`);
      reset({
        warranty_period: data.warranty_period,
        lifetime: data.lifetime,
        next_scheduled_service_date: data.next_scheduled_service_date
      });
      queryClient.invalidateQueries({ queryKey: ['device', 'details', { siteId, deviceId }] });
      mode === 'edit' && setMode('view');
    } catch (e: any) {
      notify(e.response?.data?.message || 'Something went wrong when updating the service details...');
    }
  };

  const handleClickEdit = () => setMode('edit');

  const handleClickCancel = () => {
    reset();
    setMode('view');
  };

  const {
    availability,
    failure_rate,
    warranty_period,
    lifetime,
    mtbr,
    mttr,
    next_scheduled_service_date,
    open_repair_tickets_count,
    test_interval
  } = serviceDetailData;

  return (
    <Box component="form" onSubmit={handleSubmit(onSubmit)}>
      <DetailsContainer position="relative" display="flex" flexDirection="column" flexGrow={1}>
        <Stack direction="row" p="8px" pb="16px" flexWrap="nowrap" justifyContent="space-between" alignItems="center">
          <Typography variant="h5" mb="0">
            Service Details
          </Typography>
          <Zoom in={mode === 'view'}>
            <Box borderRadius="50%" bgcolor="rgba(255, 255, 255, 0.85)">
              <IconButton
                data-testid="service_details-general_device_info-edit_btn"
                size="small"
                onClick={handleClickEdit}
              >
                <EditIcon fontSize="small" sx={{ color: '#404251' }} />
              </IconButton>
            </Box>
          </Zoom>
        </Stack>
        <Box px="8px">
          <Divider sx={{ borderBottom: '1px solid #0000003B', height: '1px', marginBottom: '8px' }} />
        </Box>
        <Table sx={{ width: '100%', height: 'auto', tableLayout: 'fixed' }} size="small">
          <TableBody>
            <TableRow>
              <FieldCell sx={{ paddingTop: mode === 'edit' ? '8px' : '8px' }} component="th" scope="row" width="40%">
                <TextBox fieldName>Lifetime</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>{lifetime}</TextBox>
                ) : (
                  <Controller
                    name="lifetime"
                    control={control}
                    rules={{
                      maxLength: {
                        value: 100,
                        message: 'Lifetime length should not exceed 100 characters.'
                      }
                    }}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        fullWidth
                        size="small"
                        error={!!errors.lifetime}
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
            {errors.lifetime?.message && (
              <TableRow>
                <FieldCell component="th" scope="row" width="40%" />
                <FieldCell component="th" scope="row" align="right">
                  <TextBox>
                    <FormHelperText sx={{ margin: 0 }} error>
                      {errors.lifetime?.message}
                    </FormHelperText>
                  </TextBox>
                </FieldCell>
              </TableRow>
            )}
            <TableRow>
              <FieldCell sx={{ paddingTop: mode === 'edit' ? '8px' : '8px' }} component="th" scope="row" width="40%">
                <TextBox fieldName>Warranty Period</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align={mode === 'edit' ? 'left' : 'right'}>
                {mode === 'view' ? (
                  <TextBox>{warranty_period}</TextBox>
                ) : (
                  <Controller
                    name="warranty_period"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <TextField
                        {...field}
                        onChange={e => onChange(e.target.value || null)}
                        value={value || ''}
                        inputRef={ref}
                        disabled={isSubmitting}
                        error={!!errors.warranty_period}
                        helperText={errors.warranty_period?.message}
                        InputProps={{
                          sx: inputStyles
                        }}
                        select
                        fullWidth
                        variant="outlined"
                        size="small"
                      >
                        <StyledSelectItem value="Active">Active</StyledSelectItem>
                        <StyledSelectItem value="End of Life">End of Life</StyledSelectItem>
                      </TextField>
                    )}
                  />
                )}
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Test Interval</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{test_interval}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Failure Rate</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{failure_rate}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Mean Time Between Failures (MTBF), Days</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{mtbr}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Mean Time to Recovery/Restore (MTTR), Days</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{mttr}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName>Availability</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{availability}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell component="th" scope="row" width="40%">
                <TextBox fieldName># of Repair Tickets Open</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                <TextBox>{open_repair_tickets_count}</TextBox>
              </FieldCell>
            </TableRow>
            <TableRow>
              <FieldCell sx={{ paddingTop: mode === 'edit' ? '8px' : '8px' }} component="th" scope="row" width="40%">
                <TextBox fieldName>Next Scheduled Service Date</TextBox>
              </FieldCell>
              <FieldCell component="th" scope="row" align="right">
                {mode === 'view' ? (
                  <TextBox>
                    {next_scheduled_service_date
                      ? dayjs(next_scheduled_service_date, 'YYYY-MM-DD', true).format('MM/DD/YYYY')
                      : ''}
                  </TextBox>
                ) : (
                  <Controller
                    name="next_scheduled_service_date"
                    control={control}
                    render={({ field: { ref, value, onChange, ...field } }) => (
                      <DatePicker
                        {...field}
                        value={value}
                        format="MM/DD/YYYY"
                        inputRef={ref}
                        onChange={val => onChange(val)}
                        disablePast
                        slotProps={{
                          textField: {
                            error: !!errors.next_scheduled_service_date,
                            helperText: errors.next_scheduled_service_date?.message,
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
          </TableBody>
        </Table>
        <Stack
          width="100%"
          direction="row"
          flexWrap="nowrap"
          alignItems="center"
          justifyContent="flex-end"
          px="8px"
          pt="16px"
          pb="8px"
        >
          {mode === 'edit' && (
            <Fade in={mode === 'edit'} timeout={{ enter: 1000, exit: 1000 }}>
              <Stack direction="row" spacing={1}>
                <Button disabled={!isValid || !isDirty || isSubmitting} variant="contained" size="small" type="submit">
                  Save
                </Button>
                <Button disabled={isSubmitting} variant="outlined" size="small" onClick={handleClickCancel}>
                  Cancel
                </Button>
              </Stack>
            </Fade>
          )}
        </Stack>
      </DetailsContainer>
    </Box>
  );
};

export default ServiceDetailCard;

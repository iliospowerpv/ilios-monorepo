import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import CoTerminusCheckResults from './CoTerminusCheckResults';

import { useNotify } from '../../../../../../../../contexts/notifications/notifications';
import { ApiClient } from '../../../../../../../../api';
import { BootstrapTooltip } from '../../../../../../../../components/common/BootstrapTooltip/BootstrapTooltip';

interface CoTerminusChecksPanelProps {
  siteId: number;
}

export const CoTerminusChecksPanel: React.FC<CoTerminusChecksPanelProps> = ({ siteId }) => {
  const notify = useNotify();
  const queryClient = useQueryClient();
  const [isCoTerminusCheckRunning, setIsCoTerminusCheckRunning] = React.useState(false);
  const [isHide, setIsHide] = React.useState(false);

  const {
    data: checkResultsData,
    isLoading: isLoadingCheckResultsData,
    error: errorLoadingCheckResultsData,
    refetch: refetchCheckResultsData
  } = useQuery({
    queryFn: () => ApiClient.dueDiligence.getCoterminusCheckResults({ siteId }),
    queryKey: ['co-terminus', 'check-results', { siteId }],
    refetchInterval: isCoTerminusCheckRunning ? 15000 : false
  });

  const {
    data: executionStatusData,
    isLoading: isLoadingExecutionStatusData,
    error: errorLoadingExecutioStatusData
  } = useQuery({
    queryFn: () => ApiClient.dueDiligence.getCoTerminusExecutionStatus({ siteId }),
    queryKey: ['co-terminus', 'execution-status', { siteId }],
    refetchInterval: isCoTerminusCheckRunning ? 15000 : 60000
  });

  React.useEffect(() => {
    const { status } = executionStatusData ?? { status: null };

    switch (status) {
      case 'Processing':
        setIsCoTerminusCheckRunning(true);
        break;
      case 'Completed':
        setIsCoTerminusCheckRunning(false);
        refetchCheckResultsData();
        notify('Coterminous check completed');
        break;
      case null:
      case 'Not Started':
        setIsCoTerminusCheckRunning(false);
        break;
      case 'Processing Failed':
      case 'Processing Start Failed':
      case 'Processing Timeout':
      case 'Unprocessable File':
        setIsCoTerminusCheckRunning(false);
        refetchCheckResultsData();
        break;
    }
  }, [executionStatusData, notify, refetchCheckResultsData]);

  React.useEffect(() => {
    if (errorLoadingExecutioStatusData) {
      const errorMessage =
        errorLoadingExecutioStatusData instanceof AxiosError
          ? errorLoadingExecutioStatusData.response?.data?.message
          : 'An error occurred when retrieving the execution status of Coterminous check ';
      notify(errorMessage);
    }
  }, [notify, errorLoadingExecutioStatusData]);

  React.useEffect(() => {
    if (errorLoadingCheckResultsData) {
      const errorMessage =
        errorLoadingCheckResultsData instanceof AxiosError
          ? errorLoadingCheckResultsData.response?.data?.message
          : 'An error occurred when retrieving results of Coterminous check ';
      notify(errorMessage);
    }
  }, [notify, errorLoadingCheckResultsData]);

  const { mutateAsync: initCoTerminusCheck, error: errorOnInitCoTerminusCheck } = useMutation({
    mutationFn: () => ApiClient.dueDiligence.initCoTerminusCheck({ siteId })
  });

  const handleRunCheck = async () => {
    try {
      setIsCoTerminusCheckRunning(true);
      const { message } = await initCoTerminusCheck();
      notify(message);
      queryClient.invalidateQueries({ queryKey: ['co-terminus'] });
    } catch (e: any) {
      setIsCoTerminusCheckRunning(false);
    }
  };

  const handleRunStop = async () => {
    try {
      await ApiClient.dueDiligence.getCoTerminusExecutionStop({ siteId });
      await queryClient.invalidateQueries({ queryKey: ['co-terminus'] });
    } catch (e: any) {
      notify(e.response?.data?.message || 'Something went wrong');
    } finally {
      setIsHide(true);
    }
  };

  const resultIsActual = executionStatusData ? executionStatusData.is_actual : true;

  const btnLabel = ['Processing', null, 'Not Started', undefined].includes(executionStatusData?.status)
    ? 'Run Сheck'
    : 'Rerun Сheck';

  return (
    <Box width="100%">
      <Stack justifyContent="space-between" direction="row" alignItems="center" spacing={1} mb={3}>
        <Typography variant="h5" fontWeight={400}>
          Coterminous
        </Typography>
        <Box>
          {executionStatusData?.is_stuck && !isHide ? (
            <BootstrapTooltip title="Use “Stop” to cancel and rerun if the process takes too long" placement="top">
              <Button size="large" variant="contained" color="primary" onClick={handleRunStop}>
                Stop
              </Button>
            </BootstrapTooltip>
          ) : null}
          <Button
            sx={{ marginLeft: '16px' }}
            size="large"
            variant="contained"
            color="primary"
            disabled={isLoadingExecutionStatusData || isCoTerminusCheckRunning || !!errorLoadingExecutioStatusData}
            startIcon={
              isLoadingExecutionStatusData || isCoTerminusCheckRunning ? (
                <CircularProgress color="inherit" size={20} />
              ) : null
            }
            onClick={handleRunCheck}
          >
            {btnLabel}
          </Button>
        </Box>
      </Stack>
      {(errorOnInitCoTerminusCheck ||
        ['Processing Failed', 'Processing Start Failed', 'Processing Timeout', 'Unprocessable File'].includes(
          executionStatusData?.status ?? ''
        )) && (
        <Box width="100%" mb="16px">
          <Alert
            sx={{
              borderRadius: '4px',
              backgroundColor: '#F7EAE6',
              '& > *': { color: '#B02E0C !important', alignItems: 'center' }
            }}
            severity="error"
          >
            An error occurred. Please try running the Coterminous check again.
          </Alert>
        </Box>
      )}
      {!resultIsActual && !isCoTerminusCheckRunning && !!checkResultsData?.items?.length && (
        <Box width="100%" mb="16px">
          <Alert
            sx={{
              borderRadius: '4px',
              backgroundColor: '#FDFBEA',
              '& > *': { color: '#5D5414 !important', alignItems: 'center' }
            }}
            severity="warning"
          >
            Some terms have been updated. Rerun the check for accurate results
          </Alert>
        </Box>
      )}
      <CoTerminusCheckResults
        isLoadingResults={isLoadingCheckResultsData}
        isCheckInProgress={isCoTerminusCheckRunning}
        hasError={
          !!errorOnInitCoTerminusCheck ||
          ['Processing Failed', 'Processing Start Failed', 'Processing Timeout', 'Unprocessable File'].includes(
            executionStatusData?.status ?? ''
          )
        }
        results={checkResultsData?.items ?? []}
        summary={checkResultsData?.summary ?? []}
      />
    </Box>
  );
};

export default CoTerminusChecksPanel;

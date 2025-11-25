import React from 'react';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import TermCheckResultComponent, { TermCheckResult } from './TermCheckResult';
import CoTerminusCheckSummary, { SummaryItem } from './CoTerminusCheckSummary';

interface CoTerminusCheckResultsListProps {
  isLoadingResults: boolean;
  isCheckInProgress: boolean;
  hasError: boolean;
  results: TermCheckResult[];
  summary: SummaryItem[];
}

const Loading: React.FC = () => (
  <Box
    width="100%"
    height="280px"
    p="16px"
    border="1px solid #0000001F"
    display="flex"
    justifyContent="center"
    alignItems="center"
    flexDirection="column"
  >
    <CircularProgress />
  </Box>
);

const NothingToShow: React.FC = () => (
  <Box
    width="100%"
    height="280px"
    p="16px"
    border="1px solid #0000001F"
    display="flex"
    justifyContent="center"
    alignItems="center"
    flexDirection="column"
  >
    <Box width="60%">
      <Typography variant="h6" textAlign="center" mb="8px">
        Nothing to show yet
      </Typography>
      <Typography variant="body2" textAlign="center" color="#4F4F4F">
        Run a check to ensure terms and dates match across documents.
      </Typography>
    </Box>
  </Box>
);

export const CoTerminusCheckResults: React.FC<CoTerminusCheckResultsListProps> = ({
  results,
  summary,
  hasError,
  isLoadingResults,
  isCheckInProgress
}) => {
  if (isLoadingResults || (isCheckInProgress && !results.length)) return <Loading />;
  if (!results.length) return <NothingToShow />;

  return (
    <Box width="100%">
      {!isCheckInProgress && !hasError && !!summary.length && <CoTerminusCheckSummary summaryItems={summary} />}
      <Stack width="100%" flexDirection="column" spacing="16px">
        {results.map(result => (
          <TermCheckResultComponent key={result.name} {...result} />
        ))}
      </Stack>
    </Box>
  );
};

export default CoTerminusCheckResults;

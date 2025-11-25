import React from 'react';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningRoundedIcon from '@mui/icons-material/WarningRounded';
import HelpIcon from '@mui/icons-material/Help';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import CircularProgress from '@mui/material/CircularProgress';

interface TermCheckResultProps {
  name: string;
  status: string;
  sources: object;
}

export const statusIconMapping: Readonly<Record<string, React.ReactNode | undefined>> = Object.freeze({
  Equal: (
    <CheckCircleIcon sx={{ color: (theme: { efficiencyColors: { good: any } }) => theme.efficiencyColors.good }} />
  ),
  'Not Equal': (
    <WarningRoundedIcon sx={{ color: (theme: { alertSeverity: { high: any } }) => theme.alertSeverity.high }} />
  ),
  Ambiguous: (
    <WarningRoundedIcon sx={{ color: (theme: { alertSeverity: { warning: any } }) => theme.alertSeverity.warning }} />
  ),
  'N/A': <HelpIcon sx={{ color: '#00000042' }} />,
  Pending: (
    <Box display="flex" justifyContent="center" alignItems="center" width="24px" height="24px">
      <CircularProgress size="20px" sx={{ color: '#0000008A' }} />
    </Box>
  ),
  Error: <ErrorOutlineIcon sx={{ color: (theme: { alertSeverity: { high: any } }) => theme.alertSeverity.high }} />
});

export const TermCheckResult: React.FC<TermCheckResultProps> = ({ name, status, sources }) => {
  const record = sources as Record<string, string>;

  return (
    <Box width="100%" p={2} border="1px solid rgba(0, 0, 0, 0.12)">
      <Stack alignItems="center" direction="row" gap={1} mb="12px">
        {statusIconMapping[status] || statusIconMapping['Error']}
        <Typography fontWeight="700" variant="subtitle1">
          {name}
        </Typography>
      </Stack>
      <Box width="100%">
        {Object.keys(record).map(key => (
          <Stack key={key} width="100%" py="8px" direction="row" gap="16px">
            <Typography variant="subtitle2" fontWeight={600} width="45%">
              {key}
            </Typography>
            <Typography variant="body2" width="55%">
              {record[key]}
            </Typography>
          </Stack>
        ))}
      </Box>
    </Box>
  );
};

export default TermCheckResult;
export type TermCheckResult = TermCheckResultProps;

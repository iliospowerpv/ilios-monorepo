import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import RefreshIcon from '@mui/icons-material/Refresh';
import IconButton from '@mui/material/IconButton';
import { styled } from '@mui/system';
import CircularProgress from '@mui/material/CircularProgress';

export const WidgetContainer = styled(Box)(() => ({
  display: 'flex',
  flexDirection: 'column',
  flexGrow: 1,
  padding: '16px',
  border: '1px solid #0000003B',
  height: '100%',
  minHeight: '360px'
}));

export const WidgetTopBar = styled(Box)(() => ({
  width: '100%',
  display: 'flex',
  justifyContent: 'space-between',
  flexWrap: 'nowrap',
  marginBottom: '6px',
  alignItems: 'flex-start'
}));

const Loading: React.FC = () => (
  <Box
    width="100%"
    height="100%"
    position="absolute"
    p="16px"
    top="0"
    display="flex"
    justifyContent="center"
    alignItems="center"
    flexDirection="column"
    bgcolor="#FFFFFF"
  >
    <CircularProgress />
  </Box>
);

const ErrorBlock: React.FC<{ message?: string }> = ({ message }) => (
  <Box
    width="100%"
    height="100%"
    position="absolute"
    p="16px"
    top="0"
    display="flex"
    justifyContent="center"
    alignItems="center"
    flexDirection="column"
    bgcolor="#FFFFFF"
  >
    <Box width="60%">
      <Typography variant="h6" textAlign="center" mb="8px">
        An error occurred while retrieving the chart data
      </Typography>
      {message && (
        <Typography variant="body2" textAlign="center" color="#4F4F4F">
          {message}
        </Typography>
      )}
    </Box>
  </Box>
);

interface WidgetWrapperProps {
  title: string;
  isLoading?: boolean;
  error?: boolean;
  errorMsg?: string;
  onClickRefetch?: () => void;
}

export const WidgetWrapper: React.FC<React.PropsWithChildren<WidgetWrapperProps>> = ({
  children,
  title,
  isLoading,
  error,
  errorMsg,
  onClickRefetch
}) => (
  <WidgetContainer>
    <WidgetTopBar>
      <Typography variant="h6" mr="8px" my="4px">
        {title}
      </Typography>
      <IconButton title="Refetch" disabled={isLoading} onClick={onClickRefetch}>
        <RefreshIcon sx={{ color: 'rgba(0, 0, 0, 0.87);' }} />
      </IconButton>
    </WidgetTopBar>
    <Box flexGrow={1} position="relative">
      {children}
      {isLoading && <Loading />}
      {error && !isLoading && <ErrorBlock message={errorMsg} />}
    </Box>
  </WidgetContainer>
);

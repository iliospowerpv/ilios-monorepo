import React from 'react';
import Box from '@mui/material/Box';
import FlagIcon from '@mui/icons-material/Flag';
import IconButton from '@mui/material/IconButton';
import CircularProgress from '@mui/material/CircularProgress';
import { BootstrapTooltip } from '../../../../../components/common/BootstrapTooltip/BootstrapTooltip';

interface DocumentPoisonPillProps {
  isPoisonPill: boolean;
  title: string | null;
  onToggle?: () => void;
  isLoading?: boolean;
}

const DocumentPoisonPill: React.FC<DocumentPoisonPillProps> = props => {
  const { isPoisonPill, title, onToggle, isLoading } = props;

  const tooltipText = isPoisonPill
    ? title || 'Flagged as poison pill — click to remove flag'
    : 'Click to flag as poison pill';

  return (
    <Box sx={{ padding: '4px', position: 'absolute', bottom: '-5px', right: 0 }}>
      <BootstrapTooltip title={tooltipText} placement="top">
        <IconButton
          sx={{ padding: '4px', margin: 0 }}
          onClick={e => {
            e.stopPropagation();
            onToggle?.();
          }}
          disabled={isLoading}
        >
          {isLoading ? (
            <CircularProgress size={20} />
          ) : (
            <FlagIcon
              sx={{
                fontSize: '24px',
                color: theme => (isPoisonPill ? theme.palette.error.main : theme.palette.text.secondary)
              }}
            />
          )}
        </IconButton>
      </BootstrapTooltip>
    </Box>
  );
};

export default DocumentPoisonPill;

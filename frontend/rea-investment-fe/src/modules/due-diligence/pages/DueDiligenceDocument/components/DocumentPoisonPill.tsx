import React from 'react';
import Box from '@mui/material/Box';
import FlagIcon from '@mui/icons-material/Flag';
import IconButton from '@mui/material/IconButton';
import { BootstrapTooltip } from '../../../../../components/common/BootstrapTooltip/BootstrapTooltip';

interface DocumentPoisonPillProps {
  isPoisonPill: boolean;
  title: string | null;
}

const DocumentPoisonPill: React.FC<DocumentPoisonPillProps> = props => {
  const { isPoisonPill, title } = props;

  return (
    <Box sx={{ padding: '4px', position: 'absolute', bottom: '-5px', right: 0 }}>
      <BootstrapTooltip title={title} placement="top">
        <IconButton sx={{ padding: '4px', margin: 0 }}>
          <FlagIcon
            sx={{
              fontSize: '24px',
              color: theme => (isPoisonPill ? theme.palette.error.main : theme.palette.text.secondary)
            }}
          />
        </IconButton>
      </BootstrapTooltip>
    </Box>
  );
};

export default DocumentPoisonPill;

import { Connection } from '../../../../../../api';
import React from 'react';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import IconButton from '@mui/material/IconButton';
import { BootstrapTooltip } from '../../../../../../components/common/BootstrapTooltip/BootstrapTooltip';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';

type ConnectionItemProps = {
  connection: any;
  onEdit: (item: Connection) => void;
  onDelete: (item: Connection) => void;
};

const ConnectionItem: React.FC<ConnectionItemProps> = ({ connection, onEdit, onDelete }) => {
  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        border: '1px solid #0000001F',
        color: 'text.secondary',
        padding: '14px 20px'
      }}
    >
      <Box sx={{ width: '80%' }}>
        <Stack direction="row" spacing={1} alignItems="center">
          <BootstrapTooltip title={connection.name} placement="top">
            <Typography
              variant="subtitle1"
              fontWeight="700"
              sx={{
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}
              gutterBottom
            >
              {connection.name}
            </Typography>
          </BootstrapTooltip>
          <Chip
            label="Verified"
            size="small"
            sx={theme => ({
              color: theme.palette.primary.main,
              background: theme.efficiencyColors.good
            })}
          />
        </Stack>
        <Typography variant="body2" gutterBottom>
          {connection.provider}
        </Typography>
      </Box>
      <Stack direction="row" spacing={1} alignItems="center">
        <IconButton sx={{ mx: '8px' }} size="small" onClick={() => onEdit(connection)}>
          <BootstrapTooltip title="Edit" placement="top">
            <EditIcon />
          </BootstrapTooltip>
        </IconButton>
        <IconButton sx={{ mx: '8px' }} size="small" onClick={() => onDelete(connection)}>
          <BootstrapTooltip title="Delete" placement="top">
            <DeleteIcon />
          </BootstrapTooltip>
        </IconButton>
      </Stack>
    </Box>
  );
};

export default ConnectionItem;

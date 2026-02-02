import React from 'react';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import CloseIcon from '@mui/icons-material/Close';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import { WIDGET_DEFINITIONS } from './widgetRegistry';

interface WidgetWrapperProps {
  widgetId: string;
  onRemove: (widgetId: string) => void;
  children: React.ReactNode;
}

export const WidgetWrapper: React.FC<WidgetWrapperProps> = ({ widgetId, onRemove, children }) => {
  const widget = WIDGET_DEFINITIONS[widgetId];
  const title = widget?.title || widgetId;

  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Box
        className="drag-handle"
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 1,
          py: 0.5,
          borderBottom: theme => `1px solid ${theme.palette.divider}`,
          backgroundColor: theme => theme.palette.grey[50],
          cursor: 'grab',
          '&:active': { cursor: 'grabbing' }
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <DragIndicatorIcon sx={{ color: 'text.secondary', fontSize: 20 }} />
          <Typography variant="subtitle2" fontWeight={500}>
            {title}
          </Typography>
        </Box>
        <IconButton size="small" onClick={() => onRemove(widgetId)} sx={{ '&:hover': { color: 'error.main' } }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>
      <CardContent sx={{ flex: 1, overflow: 'auto', p: 0, '&:last-child': { pb: 0 } }}>{children}</CardContent>
    </Card>
  );
};

export default WidgetWrapper;

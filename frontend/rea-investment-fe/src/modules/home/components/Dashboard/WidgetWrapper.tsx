import React from 'react';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import { WIDGET_DEFINITIONS } from './widgetRegistry';

interface WidgetWrapperProps {
  widgetId: string;
  onRemove: (widgetId: string) => void;
  children: React.ReactNode;
  showHeader?: boolean;
}

export const WidgetWrapper: React.FC<WidgetWrapperProps> = ({
  widgetId,
  onRemove,
  children,
  showHeader = true
}) => {
  const widget = WIDGET_DEFINITIONS[widgetId];
  const title = widget?.title || widgetId;

  return (
    <Card
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}
    >
      {showHeader && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            px: 1,
            py: 0.5,
            borderBottom: theme => `1px solid ${theme.palette.divider}`,
            backgroundColor: theme => theme.custom.surface.lightweight,
            cursor: 'grab'
          }}
          className="drag-handle"
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <DragIndicatorIcon sx={{ color: 'text.secondary', fontSize: 20 }} />
            <Typography variant="subtitle2" fontWeight={500}>
              {title}
            </Typography>
          </Box>
          <IconButton
            size="small"
            onClick={() => onRemove(widgetId)}
            sx={{ '&:hover': { color: 'error.main' } }}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>
      )}
      <CardContent
        sx={{
          flex: 1,
          overflow: 'auto',
          p: showHeader ? 2 : 0,
          '&:last-child': { pb: showHeader ? 2 : 0 }
        }}
      >
        {children}
      </CardContent>
    </Card>
  );
};

export default WidgetWrapper;

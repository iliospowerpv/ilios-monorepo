import React from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import ListItemIcon from '@mui/material/ListItemIcon';
import Checkbox from '@mui/material/Checkbox';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import AddIcon from '@mui/icons-material/Add';
import { WIDGET_DEFINITIONS } from './widgetRegistry';

interface AddWidgetDialogProps {
  open: boolean;
  onClose: () => void;
  visibleWidgets: string[];
  onAddWidget: (widgetId: string) => void;
}

export const AddWidgetDialog: React.FC<AddWidgetDialogProps> = ({
  open,
  onClose,
  visibleWidgets,
  onAddWidget
}) => {
  const availableWidgets = Object.values(WIDGET_DEFINITIONS).filter(
    widget => !visibleWidgets.includes(widget.id)
  );

  const handleAddWidget = (widgetId: string) => {
    onAddWidget(widgetId);
    if (availableWidgets.length === 1) {
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add Widget</DialogTitle>
      <DialogContent dividers>
        {availableWidgets.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography color="text.secondary">
              All available widgets are already on your dashboard.
            </Typography>
          </Box>
        ) : (
          <List>
            {availableWidgets.map(widget => (
              <ListItem key={widget.id} disablePadding>
                <ListItemButton onClick={() => handleAddWidget(widget.id)}>
                  <ListItemIcon>
                    <AddIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText primary={widget.title} secondary={widget.description} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default AddWidgetDialog;

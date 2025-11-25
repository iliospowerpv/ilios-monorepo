import React, { useState, useEffect } from 'react';
import { ColDef } from 'ag-grid-community';
import { Button, Box } from '@mui/material';
import Grid from '@mui/material/Grid';
import Checkbox from '@mui/material/Checkbox';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import FormControlLabel from '@mui/material/FormControlLabel';
import CloseIcon from '@mui/icons-material/Close';
import IconButton from '@mui/material/IconButton';

interface ColumnProp extends ColDef {
  isDefault: boolean;
  checked: boolean;
}
interface ColumnsProps {
  open: boolean;
  columns: ColumnProp[];
  onApply: (columns: ColumnProp[]) => void;
  onClose: () => void;
}

const ColumnsModal = ({ open, columns, onApply, onClose }: ColumnsProps) => {
  const [checkedItems, setCheckedItems] = useState<ColumnProp[]>(columns);
  const [itemLength, setItemLength] = useState<number>(0);
  const [isAnyCheckboxChecked, setIsAnyCheckboxChecked] = useState<boolean>(false);

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>, index: number) => {
    const newCheckedItems = [...checkedItems];
    newCheckedItems[index] = { ...newCheckedItems[index], checked: event.target.checked };
    setCheckedItems(newCheckedItems);
  };

  const handleApply = () => {
    onApply(checkedItems);
    onClose();
  };

  const handleClear = () => {
    const resetChecked = checkedItems.map((item: ColumnProp) => ({
      ...item,
      checked: item.isDefault || false
    }));

    setCheckedItems(resetChecked);
  };

  useEffect(() => {
    const filteredItems = checkedItems.filter((item: ColumnProp) => !item.isDefault);
    setItemLength(filteredItems.length);
  }, []);

  useEffect(() => {
    const isChecked = checkedItems.some((item: ColumnProp) => !item.isDefault && item.checked);
    setIsAnyCheckboxChecked(isChecked);
  }, [checkedItems]);

  return (
    <>
      <Dialog
        open={open}
        onClose={onClose}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
        fullWidth={true}
      >
        <DialogTitle id="alert-dialog-title" sx={{ bgcolor: 'primary.main', color: 'secondary.main' }}>
          Set columns to display
        </DialogTitle>
        <IconButton
          aria-label="close"
          onClick={onClose}
          sx={{
            position: 'absolute',
            right: 10,
            top: 12,
            color: theme => theme.palette.secondary.main
          }}
        >
          <CloseIcon />
        </IconButton>
        <DialogContent sx={{ py: 0 }}>
          <Box sx={{ p: '20px' }}>
            <Grid container spacing={1}>
              {checkedItems.map(
                (item: any, index: number) =>
                  !item.isDefault && (
                    <Grid item xs={itemLength <= 4 ? 12 : 6} key={index}>
                      <FormControlLabel
                        control={<Checkbox checked={item.checked} onChange={event => handleChange(event, index)} />}
                        label={item.headerName}
                      />
                    </Grid>
                  )
              )}
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button disabled={!isAnyCheckboxChecked} onClick={handleClear}>
            Clear
          </Button>
          <Button onClick={handleApply} autoFocus>
            Apply
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default ColumnsModal;

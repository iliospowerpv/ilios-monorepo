import React from 'react';
import { Button, Box, Typography, Stack, Chip } from '@mui/material';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import Select, { SelectChangeEvent } from '@mui/material/Select';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { State, OwnershipStructure, Stage } from '../../../../../utils/asset-managment';
import { Dayjs } from 'dayjs';

interface FiltersProps {
  open: boolean;
  handleClose: () => void;
}

const noBottomLineStyles = {
  '& .MuiInputBase-root:not(.Mui-disabled, .Mui-error)': {
    '& .MuiFilledInput-input': {
      paddingBottom: '14px',
      paddingTop: '14px'
    },
    '&::before, &:hover::before, &.Mui-focused::after': {
      borderBottomColor: 'transparent',
      transform: 'scaleX(0)'
    }
  }
};

const FiltersModal = ({ open, handleClose }: FiltersProps) => {
  const [company, setCompany] = React.useState('');
  const [stage, setStage] = React.useState('');
  const [state, setState] = React.useState('');
  const [ownership, setOwnership] = React.useState('');
  const [status, setStatus] = React.useState('');
  const [date, setDate] = React.useState<Dayjs | null>(null);

  const handleChangeCompany = (event: SelectChangeEvent) => {
    setCompany(event.target.value as string);
  };

  const handleChangeStage = (event: SelectChangeEvent) => {
    setStage(event.target.value as string);
  };

  const handleChangeState = (event: SelectChangeEvent) => {
    setState(event.target.value as string);
  };

  const handleChangeOwnership = (event: SelectChangeEvent) => {
    setOwnership(event.target.value as string);
  };

  const handleChangeDate = (value: Dayjs | null) => {
    setDate(value);
  };

  const handleClear = () => {
    setCompany('');
    setStage('');
    setState('');
    setOwnership('');
    setDate(null);
    setStatus('');
  };

  return (
    <>
      <Dialog
        open={open}
        onClose={handleClose}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
        fullWidth={true}
      >
        <DialogTitle id="alert-dialog-title" sx={{ bgcolor: 'primary.main', color: 'secondary.main' }}>
          Add Filters
        </DialogTitle>
        <DialogContent>
          <Box sx={{ p: '20px' }}>
            <Typography variant="subtitle2" display="block" fontWeight="bold" my="8px">
              Company name
            </Typography>
            <FormControl sx={noBottomLineStyles} variant="filled" fullWidth>
              <Select value={company} onChange={handleChangeCompany} displayEmpty>
                <MenuItem value="">Select</MenuItem>
                <MenuItem value={10}>Ten</MenuItem>
                <MenuItem value={20}>Twenty</MenuItem>
                <MenuItem value={30}>Thirty</MenuItem>
              </Select>
            </FormControl>
            <Typography variant="subtitle2" display="block" fontWeight="bold" my="8px">
              Status
            </Typography>
            <Stack direction="row" spacing={1}>
              <Chip
                color="success"
                size="small"
                label="Placed in service"
                sx={{ border: status === 'sales_pipeline' ? '1px solid black' : 'none' }}
                onClick={() => {
                  setStatus('sales_pipeline');
                }}
              />
              <Chip
                color="warning"
                size="small"
                label="Under construction"
                sx={{ border: status === 'under_construction' ? '1px solid black' : 'none' }}
                onClick={() => {
                  setStatus('under_construction');
                }}
              />
              <Chip
                size="small"
                label="Sales pipeline"
                sx={{ border: status === 'placed_in_service' ? '1px solid black' : 'none' }}
                onClick={() => {
                  setStatus('placed_in_service');
                }}
              />
            </Stack>
            <Typography variant="subtitle2" display="block" fontWeight="bold" my="8px">
              Stage
            </Typography>
            <FormControl sx={noBottomLineStyles} variant="filled" fullWidth>
              <Select value={stage} onChange={handleChangeStage} displayEmpty>
                <MenuItem value="">Select</MenuItem>
                {Object.entries(Stage).map(([key, value]) => (
                  <MenuItem key={key} value={key}>
                    {value}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Typography variant="subtitle2" display="block" fontWeight="bold" my="8px">
              Ownership structure
            </Typography>
            <FormControl sx={noBottomLineStyles} variant="filled" fullWidth>
              <Select value={ownership} onChange={handleChangeOwnership} displayEmpty>
                <MenuItem value="">Select</MenuItem>
                {Object.entries(OwnershipStructure).map(([key, value]) => (
                  <MenuItem key={key} value={key}>
                    {value}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Typography variant="subtitle2" display="block" fontWeight="bold" my="8px">
              State
            </Typography>
            <FormControl sx={noBottomLineStyles} variant="filled" fullWidth>
              <Select value={state} onChange={handleChangeState} displayEmpty>
                <MenuItem value="">Select</MenuItem>
                {Object.entries(State).map(([key, value]) => (
                  <MenuItem key={key} value={key}>
                    {value}
                  </MenuItem>
                ))}
              </Select>
              <Typography variant="subtitle2" display="block" fontWeight="bold" my="8px">
                Placed in Service
              </Typography>
              <LocalizationProvider dateAdapter={AdapterDayjs}>
                <DatePicker sx={noBottomLineStyles} value={date} onChange={newValue => handleChangeDate(newValue)} />
              </LocalizationProvider>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClear}>Clear</Button>
          <Button onClick={handleClose} autoFocus>
            Apply
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default FiltersModal;

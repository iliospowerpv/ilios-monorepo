import React, { useState, useEffect } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Stack from '@mui/material/Stack';
import { FinanceBudget, FinanceBudgetStatus } from '../types';

interface BudgetFormDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: Partial<FinanceBudget>) => Promise<unknown>;
  budget?: FinanceBudget;
  siteId?: number;
}

export const BudgetFormDialog: React.FC<BudgetFormDialogProps> = ({ open, onClose, onSubmit, budget, siteId }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [status, setStatus] = useState<FinanceBudgetStatus>(FinanceBudgetStatus.Draft);
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (budget) {
      setName(budget.name);
      setDescription(budget.description || '');
      setStatus(budget.status);
      setPeriodStart(budget.period_start || '');
      setPeriodEnd(budget.period_end || '');
    } else {
      setName('');
      setDescription('');
      setStatus(FinanceBudgetStatus.Draft);
      setPeriodStart('');
      setPeriodEnd('');
    }
  }, [budget, open]);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await onSubmit({
        name,
        description: description || undefined,
        status,
        period_start: periodStart || undefined,
        period_end: periodEnd || undefined,
        site_id: siteId
      });
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const isEdit = !!budget;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{isEdit ? 'Edit Budget' : 'Create Budget'}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <TextField
            label="Budget Name"
            value={name}
            onChange={e => setName(e.target.value)}
            required
            fullWidth
          />
          <TextField
            label="Description"
            value={description}
            onChange={e => setDescription(e.target.value)}
            multiline
            rows={2}
            fullWidth
          />
          <FormControl fullWidth>
            <InputLabel>Status</InputLabel>
            <Select value={status} onChange={e => setStatus(e.target.value as FinanceBudgetStatus)} label="Status">
              <MenuItem value={FinanceBudgetStatus.Draft}>Draft</MenuItem>
              <MenuItem value={FinanceBudgetStatus.Active}>Active</MenuItem>
              <MenuItem value={FinanceBudgetStatus.Closed}>Closed</MenuItem>
            </Select>
          </FormControl>
          <TextField
            label="Period Start"
            type="date"
            value={periodStart}
            onChange={e => setPeriodStart(e.target.value)}
            InputLabelProps={{ shrink: true }}
            fullWidth
          />
          <TextField
            label="Period End"
            type="date"
            value={periodEnd}
            onChange={e => setPeriodEnd(e.target.value)}
            InputLabelProps={{ shrink: true }}
            fullWidth
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} variant="contained" disabled={loading || !name}>
          {isEdit ? 'Save' : 'Create'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default BudgetFormDialog;

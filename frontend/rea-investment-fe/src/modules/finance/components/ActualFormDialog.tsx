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
import InputAdornment from '@mui/material/InputAdornment';
import { FinanceActual, FinanceBudgetCategory, FinanceActualSource, FinanceVendor } from '../types';

interface ActualFormDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: Partial<FinanceActual>) => Promise<unknown>;
  siteId?: number;
  vendors: FinanceVendor[];
}

export const ActualFormDialog: React.FC<ActualFormDialogProps> = ({ open, onClose, onSubmit, siteId, vendors }) => {
  const [category, setCategory] = useState<FinanceBudgetCategory>(FinanceBudgetCategory.Other);
  const [vendorId, setVendorId] = useState<number | ''>('');
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [transactionDate, setTransactionDate] = useState('');
  const [referenceId, setReferenceId] = useState('');
  const [sourceSystem, setSourceSystem] = useState<FinanceActualSource>(FinanceActualSource.Manual);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      setCategory(FinanceBudgetCategory.Other);
      setVendorId('');
      setDescription('');
      setAmount('');
      setTransactionDate(new Date().toISOString().split('T')[0]);
      setReferenceId('');
      setSourceSystem(FinanceActualSource.Manual);
    }
  }, [open]);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await onSubmit({
        category,
        vendor_id: vendorId ? Number(vendorId) : undefined,
        description: description || undefined,
        amount: Number(amount),
        transaction_date: transactionDate,
        reference_id: referenceId || undefined,
        source_system: sourceSystem,
        site_id: siteId
      });
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Record Actual</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <FormControl fullWidth required>
            <InputLabel>Category</InputLabel>
            <Select value={category} onChange={e => setCategory(e.target.value as FinanceBudgetCategory)} label="Category">
              <MenuItem value={FinanceBudgetCategory.Development}>Development</MenuItem>
              <MenuItem value={FinanceBudgetCategory.Construction}>Construction</MenuItem>
              <MenuItem value={FinanceBudgetCategory.Interconnection}>Interconnection</MenuItem>
              <MenuItem value={FinanceBudgetCategory.Permitting}>Permitting</MenuItem>
              <MenuItem value={FinanceBudgetCategory.Equipment}>Equipment</MenuItem>
              <MenuItem value={FinanceBudgetCategory.Labor}>Labor</MenuItem>
              <MenuItem value={FinanceBudgetCategory.Engineering}>Engineering</MenuItem>
              <MenuItem value={FinanceBudgetCategory.Legal}>Legal</MenuItem>
              <MenuItem value={FinanceBudgetCategory.Insurance}>Insurance</MenuItem>
              <MenuItem value={FinanceBudgetCategory.OM}>O&M</MenuItem>
              <MenuItem value={FinanceBudgetCategory.Administrative}>Administrative</MenuItem>
              <MenuItem value={FinanceBudgetCategory.Contingency}>Contingency</MenuItem>
              <MenuItem value={FinanceBudgetCategory.Other}>Other</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel>Vendor</InputLabel>
            <Select value={vendorId} onChange={e => setVendorId(e.target.value as number)} label="Vendor">
              <MenuItem value="">
                <em>None</em>
              </MenuItem>
              {vendors.map(v => (
                <MenuItem key={v.id} value={v.id}>
                  {v.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            label="Amount"
            type="number"
            value={amount}
            onChange={e => setAmount(e.target.value)}
            required
            fullWidth
            InputProps={{
              startAdornment: <InputAdornment position="start">$</InputAdornment>
            }}
          />
          <TextField
            label="Description"
            value={description}
            onChange={e => setDescription(e.target.value)}
            multiline
            rows={2}
            fullWidth
          />
          <TextField
            label="Transaction Date"
            type="date"
            value={transactionDate}
            onChange={e => setTransactionDate(e.target.value)}
            required
            InputLabelProps={{ shrink: true }}
            fullWidth
          />
          <TextField
            label="Reference ID"
            value={referenceId}
            onChange={e => setReferenceId(e.target.value)}
            fullWidth
            placeholder="e.g., QB-12345"
          />
          <FormControl fullWidth>
            <InputLabel>Source System</InputLabel>
            <Select value={sourceSystem} onChange={e => setSourceSystem(e.target.value as FinanceActualSource)} label="Source System">
              <MenuItem value={FinanceActualSource.Manual}>Manual Entry</MenuItem>
              <MenuItem value={FinanceActualSource.QuickBooks}>QuickBooks</MenuItem>
              <MenuItem value={FinanceActualSource.Gravity}>Gravity</MenuItem>
              <MenuItem value={FinanceActualSource.Other}>Other</MenuItem>
            </Select>
          </FormControl>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} variant="contained" disabled={loading || !amount || !transactionDate}>
          Record
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ActualFormDialog;

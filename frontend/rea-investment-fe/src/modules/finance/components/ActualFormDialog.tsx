import React, { useState, useEffect } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Stack from '@mui/material/Stack';
import InputAdornment from '@mui/material/InputAdornment';
import { FinanceActual, FinanceBudgetCategory, FinanceActualSource, FinanceVendor } from '../types';
import { SearchableSelect, SearchableSelectOption } from '../../../components/common/SearchableSelect/SearchableSelect';

const categoryOptions: SearchableSelectOption[] = [
  { label: 'Development', value: FinanceBudgetCategory.Development },
  { label: 'Construction', value: FinanceBudgetCategory.Construction },
  { label: 'Interconnection', value: FinanceBudgetCategory.Interconnection },
  { label: 'Permitting', value: FinanceBudgetCategory.Permitting },
  { label: 'Equipment', value: FinanceBudgetCategory.Equipment },
  { label: 'Labor', value: FinanceBudgetCategory.Labor },
  { label: 'Engineering', value: FinanceBudgetCategory.Engineering },
  { label: 'Legal', value: FinanceBudgetCategory.Legal },
  { label: 'Insurance', value: FinanceBudgetCategory.Insurance },
  { label: 'O&M', value: FinanceBudgetCategory.OM },
  { label: 'Administrative', value: FinanceBudgetCategory.Administrative },
  { label: 'Contingency', value: FinanceBudgetCategory.Contingency },
  { label: 'Other', value: FinanceBudgetCategory.Other }
];

const sourceSystemOptions: SearchableSelectOption[] = [
  { label: 'Manual Entry', value: FinanceActualSource.Manual },
  { label: 'QuickBooks', value: FinanceActualSource.QuickBooks },
  { label: 'Gravity', value: FinanceActualSource.Gravity },
  { label: 'Other', value: FinanceActualSource.Other }
];

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

  const vendorOptions: SearchableSelectOption[] = vendors.map(v => ({
    label: v.name,
    value: v.id
  }));

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Record Actual</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <SearchableSelect
            options={categoryOptions}
            value={category}
            onChange={val => setCategory(val as FinanceBudgetCategory)}
            label="Category"
            required
          />
          <SearchableSelect
            options={vendorOptions}
            value={vendorId || null}
            onChange={val => setVendorId(val ? (val as number) : '')}
            label="Vendor"
          />
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
          <SearchableSelect
            options={sourceSystemOptions}
            value={sourceSystem}
            onChange={val => setSourceSystem(val as FinanceActualSource)}
            label="Source System"
          />
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

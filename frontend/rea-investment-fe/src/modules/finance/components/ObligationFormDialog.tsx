import React, { useState, useEffect } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Stack from '@mui/material/Stack';
import InputAdornment from '@mui/material/InputAdornment';
import { FinanceObligation, FinanceObligationType, FinanceVendor } from '../types';
import { SearchableSelect, SearchableSelectOption } from '../../../components/common/SearchableSelect/SearchableSelect';

const obligationTypeOptions: SearchableSelectOption[] = [
  { label: 'Invoice', value: FinanceObligationType.Invoice },
  { label: 'Milestone', value: FinanceObligationType.Milestone },
  { label: 'Retainer', value: FinanceObligationType.Retainer },
  { label: 'Change Order', value: FinanceObligationType.ChangeOrder },
  { label: 'Service Call', value: FinanceObligationType.ServiceCall },
  { label: 'Other', value: FinanceObligationType.Other }
];

interface ObligationFormDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: Partial<FinanceObligation>) => Promise<unknown>;
  obligation?: FinanceObligation;
  siteId?: number;
  vendors: FinanceVendor[];
  onCreateVendor?: () => void;
}

export const ObligationFormDialog: React.FC<ObligationFormDialogProps> = ({
  open,
  onClose,
  onSubmit,
  obligation,
  siteId,
  vendors,
  onCreateVendor
}) => {
  const [obligationType, setObligationType] = useState<FinanceObligationType>(FinanceObligationType.Invoice);
  const [vendorId, setVendorId] = useState<number | ''>('');
  const [description, setDescription] = useState('');
  const [amountRequested, setAmountRequested] = useState('');
  const [requestedDate, setRequestedDate] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [referenceNumber, setReferenceNumber] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (obligation) {
      setObligationType(obligation.obligation_type);
      setVendorId(obligation.vendor_id || '');
      setDescription(obligation.description || '');
      setAmountRequested(String(obligation.amount_requested));
      setRequestedDate(obligation.requested_date?.split('T')[0] || '');
      setDueDate(obligation.due_date?.split('T')[0] || '');
      setReferenceNumber(obligation.reference_number || '');
    } else {
      setObligationType(FinanceObligationType.Invoice);
      setVendorId('');
      setDescription('');
      setAmountRequested('');
      setRequestedDate(new Date().toISOString().split('T')[0]);
      setDueDate('');
      setReferenceNumber('');
    }
  }, [obligation, open]);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await onSubmit({
        obligation_type: obligationType,
        vendor_id: vendorId ? Number(vendorId) : undefined,
        description: description || undefined,
        amount_requested: Number(amountRequested),
        requested_date: requestedDate,
        due_date: dueDate || undefined,
        reference_number: referenceNumber || undefined,
        site_id: siteId
      });
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const isEdit = !!obligation;

  const vendorOptions: SearchableSelectOption[] = vendors.map(v => ({
    label: v.name,
    value: v.id
  }));

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{isEdit ? 'Edit Obligation' : 'Create Obligation'}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <SearchableSelect
            options={obligationTypeOptions}
            value={obligationType}
            onChange={val => setObligationType(val as FinanceObligationType)}
            label="Type"
            required
          />
          <Stack direction="row" spacing={1} alignItems="flex-end">
            <SearchableSelect
              options={vendorOptions}
              value={vendorId || null}
              onChange={val => setVendorId(val ? (val as number) : '')}
              label="Vendor"
            />
            {onCreateVendor && (
              <Button variant="outlined" size="small" onClick={onCreateVendor} sx={{ whiteSpace: 'nowrap' }}>
                + New
              </Button>
            )}
          </Stack>
          <TextField
            label="Amount"
            type="number"
            value={amountRequested}
            onChange={e => setAmountRequested(e.target.value)}
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
            label="Requested Date"
            type="date"
            value={requestedDate}
            onChange={e => setRequestedDate(e.target.value)}
            required
            InputLabelProps={{ shrink: true }}
            fullWidth
          />
          <TextField
            label="Due Date"
            type="date"
            value={dueDate}
            onChange={e => setDueDate(e.target.value)}
            InputLabelProps={{ shrink: true }}
            fullWidth
          />
          <TextField
            label="Reference Number"
            value={referenceNumber}
            onChange={e => setReferenceNumber(e.target.value)}
            fullWidth
            placeholder="e.g., INV-2024-001"
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} variant="contained" disabled={loading || !amountRequested || !requestedDate}>
          {isEdit ? 'Save' : 'Create'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ObligationFormDialog;

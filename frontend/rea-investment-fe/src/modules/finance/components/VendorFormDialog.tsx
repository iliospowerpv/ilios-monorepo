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
import FormControlLabel from '@mui/material/FormControlLabel';
import Switch from '@mui/material/Switch';
import { FinanceVendor, FinanceVendorType } from '../types';

interface VendorFormDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: Partial<FinanceVendor>) => Promise<unknown>;
  vendor?: FinanceVendor;
}

export const VendorFormDialog: React.FC<VendorFormDialogProps> = ({ open, onClose, onSubmit, vendor }) => {
  const [name, setName] = useState('');
  const [vendorType, setVendorType] = useState<FinanceVendorType>(FinanceVendorType.Other);
  const [contactName, setContactName] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [notes, setNotes] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (vendor) {
      setName(vendor.name);
      setVendorType(vendor.vendor_type);
      setContactName(vendor.contact_name || '');
      setContactEmail(vendor.contact_email || '');
      setContactPhone(vendor.contact_phone || '');
      setNotes(vendor.notes || '');
      setIsActive(vendor.is_active);
    } else {
      setName('');
      setVendorType(FinanceVendorType.Other);
      setContactName('');
      setContactEmail('');
      setContactPhone('');
      setNotes('');
      setIsActive(true);
    }
  }, [vendor, open]);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await onSubmit({
        name,
        vendor_type: vendorType,
        contact_name: contactName || undefined,
        contact_email: contactEmail || undefined,
        contact_phone: contactPhone || undefined,
        notes: notes || undefined,
        is_active: isActive
      });
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const isEdit = !!vendor;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{isEdit ? 'Edit Vendor' : 'Create Vendor'}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <TextField label="Vendor Name" value={name} onChange={e => setName(e.target.value)} required fullWidth />
          <FormControl fullWidth required>
            <InputLabel>Type</InputLabel>
            <Select value={vendorType} onChange={e => setVendorType(e.target.value as FinanceVendorType)} label="Type">
              <MenuItem value={FinanceVendorType.EPC}>EPC</MenuItem>
              <MenuItem value={FinanceVendorType.OM}>O&M</MenuItem>
              <MenuItem value={FinanceVendorType.Insurance}>Insurance</MenuItem>
              <MenuItem value={FinanceVendorType.Utility}>Utility</MenuItem>
              <MenuItem value={FinanceVendorType.Engineering}>Engineering</MenuItem>
              <MenuItem value={FinanceVendorType.Legal}>Legal</MenuItem>
              <MenuItem value={FinanceVendorType.Accounting}>Accounting</MenuItem>
              <MenuItem value={FinanceVendorType.Other}>Other</MenuItem>
            </Select>
          </FormControl>
          <TextField
            label="Contact Name"
            value={contactName}
            onChange={e => setContactName(e.target.value)}
            fullWidth
          />
          <TextField
            label="Contact Email"
            type="email"
            value={contactEmail}
            onChange={e => setContactEmail(e.target.value)}
            fullWidth
          />
          <TextField
            label="Contact Phone"
            value={contactPhone}
            onChange={e => setContactPhone(e.target.value)}
            fullWidth
          />
          <TextField
            label="Notes"
            value={notes}
            onChange={e => setNotes(e.target.value)}
            multiline
            rows={2}
            fullWidth
          />
          <FormControlLabel
            control={<Switch checked={isActive} onChange={e => setIsActive(e.target.checked)} />}
            label="Active"
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

export default VendorFormDialog;

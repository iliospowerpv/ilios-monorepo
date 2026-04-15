import React, { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Chip from '@mui/material/Chip';

import { ApiClient } from '../../../../api';
import type { Contact, ContactCreate, ContactUpdate, ContactScopeType } from '../../../../api';
import { useNotify } from '../../../../contexts/notifications/notifications';

interface ContactFormModalProps {
  open: boolean;
  onClose: () => void;
  scopeType: ContactScopeType;
  scopeId: number;
  contact?: Contact | null;
  onSuccess?: () => void;
}

interface FormData {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  title: string;
  organization: string;
  notes: string;
  tags: string[];
}

const INITIAL_FORM: FormData = {
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  title: '',
  organization: '',
  notes: '',
  tags: []
};

export const ContactFormModal: React.FC<ContactFormModalProps> = ({
  open,
  onClose,
  scopeType,
  scopeId,
  contact,
  onSuccess
}) => {
  const queryClient = useQueryClient();
  const notify = useNotify();
  const [formData, setFormData] = useState<FormData>(INITIAL_FORM);
  const [error, setError] = useState<string | null>(null);
  const [tagInput, setTagInput] = useState('');

  const isEditing = !!contact;

  useEffect(() => {
    if (open) {
      if (contact) {
        setFormData({
          first_name: contact.first_name,
          last_name: contact.last_name,
          email: contact.email || '',
          phone: contact.phone || '',
          title: contact.title || '',
          organization: contact.organization || '',
          notes: contact.notes || '',
          tags: contact.tags || []
        });
      } else {
        setFormData(INITIAL_FORM);
      }
      setError(null);
    }
  }, [open, contact]);

  const createMutation = useMutation({
    mutationFn: (data: ContactCreate) => ApiClient.contacts.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      notify('Contact created successfully');
      onClose();
      onSuccess?.();
    },
    onError: (err: any) => {
      const message = err.response?.data?.detail || 'Failed to create contact';
      setError(message);
    }
  });

  const updateMutation = useMutation({
    mutationFn: (data: ContactUpdate) => ApiClient.contacts.update(contact!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      notify('Contact updated successfully');
      onClose();
      onSuccess?.();
    },
    onError: (err: any) => {
      const message = err.response?.data?.detail || 'Failed to update contact';
      setError(message);
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!formData.first_name.trim() || !formData.last_name.trim()) {
      setError('First name and last name are required');
      return;
    }

    if (isEditing) {
      const updateData: ContactUpdate = {
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim(),
        email: formData.email.trim() || null,
        phone: formData.phone.trim() || null,
        title: formData.title.trim() || null,
        organization: formData.organization.trim() || null,
        notes: formData.notes.trim() || null,
        tags: formData.tags.length > 0 ? formData.tags : null
      };
      updateMutation.mutate(updateData);
    } else {
      const createData: ContactCreate = {
        scope_type: scopeType,
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim(),
        email: formData.email.trim() || null,
        phone: formData.phone.trim() || null,
        title: formData.title.trim() || null,
        organization: formData.organization.trim() || null,
        notes: formData.notes.trim() || null,
        tags: formData.tags.length > 0 ? formData.tags : null
      };
      if (scopeType === 'portfolio') {
        createData.portfolio_id = scopeId;
      } else if (scopeType === 'company') {
        createData.company_id = scopeId;
      } else if (scopeType === 'project') {
        createData.project_id = scopeId;
      }
      createMutation.mutate(createData);
    }
  };

  const handleChange = (field: keyof FormData) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData(prev => ({ ...prev, [field]: e.target.value }));
  };

  const handleAddTag = () => {
    const tag = tagInput.trim();
    if (tag && !formData.tags.includes(tag)) {
      setFormData(prev => ({ ...prev, tags: [...prev.tags, tag] }));
      setTagInput('');
    }
  };

  const handleDeleteTag = (tagToDelete: string) => {
    setFormData(prev => ({ ...prev, tags: prev.tags.filter(tag => tag !== tagToDelete) }));
  };

  const isLoading = createMutation.isPending || updateMutation.isPending;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit}>
        <DialogTitle>{isEditing ? 'Edit Contact' : 'Add Contact'}</DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={6}>
              <TextField
                label="First Name"
                value={formData.first_name}
                onChange={handleChange('first_name')}
                fullWidth
                required
                disabled={isLoading}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                label="Last Name"
                value={formData.last_name}
                onChange={handleChange('last_name')}
                fullWidth
                required
                disabled={isLoading}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Email"
                type="email"
                value={formData.email}
                onChange={handleChange('email')}
                fullWidth
                disabled={isLoading}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Phone"
                value={formData.phone}
                onChange={handleChange('phone')}
                fullWidth
                disabled={isLoading}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Title"
                value={formData.title}
                onChange={handleChange('title')}
                fullWidth
                disabled={isLoading}
                placeholder="e.g. Asset Manager, Investor, Broker"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Organization"
                value={formData.organization}
                onChange={handleChange('organization')}
                fullWidth
                disabled={isLoading}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Notes"
                value={formData.notes}
                onChange={handleChange('notes')}
                fullWidth
                multiline
                rows={3}
                disabled={isLoading}
              />
            </Grid>
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1 }}>
                {formData.tags.map(tag => (
                  <Chip key={tag} label={tag} onDelete={() => handleDeleteTag(tag)} size="small" />
                ))}
              </Box>
              <TextField
                label="Add Tag"
                value={tagInput}
                onChange={e => setTagInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddTag();
                  }
                }}
                fullWidth
                disabled={isLoading}
                placeholder="Press Enter to add tag"
                size="small"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="submit" variant="contained" disabled={isLoading}>
            {isLoading ? <CircularProgress size={24} /> : isEditing ? 'Save Changes' : 'Add Contact'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default ContactFormModal;

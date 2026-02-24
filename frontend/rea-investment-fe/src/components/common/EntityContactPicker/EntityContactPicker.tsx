import React, { useState, useCallback, useEffect } from 'react';
import Autocomplete from '@mui/material/Autocomplete';
import TextField from '@mui/material/TextField';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import AddIcon from '@mui/icons-material/Add';
import { ApiClient } from '../../../api';
import type { Contact } from '../../../api/contacts';

interface AddNewOption {
  id: -1;
  first_name: string;
  last_name: string;
  isAddNew: true;
}

type OptionType = Contact | AddNewOption;

function isAddNewOption(option: OptionType): option is AddNewOption {
  return 'isAddNew' in option && option.isAddNew === true;
}

interface EntityContactPickerProps {
  entityId: number | null;
  portfolioId: number;
  value: number | null;
  onChange: (contactId: number | null, contact: Contact | null) => void;
  label?: string;
  disabled?: boolean;
  size?: 'small' | 'medium';
}

export const EntityContactPicker: React.FC<EntityContactPickerProps> = ({
  entityId,
  portfolioId,
  value,
  onChange,
  label = 'Contact',
  disabled = false,
  size = 'small'
}) => {
  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [options, setOptions] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedContact, setSelectedContact] = useState<Contact | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    title: ''
  });
  const [creating, setCreating] = useState(false);

  const fetchOptions = useCallback(
    async (search: string) => {
      if (!portfolioId) return;
      setLoading(true);
      try {
        const result = await ApiClient.contacts.list({
          scope_type: 'portfolio',
          portfolio_id: portfolioId,
          entity_id: entityId || undefined,
          search: search || undefined,
          limit: 50
        });
        setOptions(result.items);
      } catch {
        setOptions([]);
      } finally {
        setLoading(false);
      }
    },
    [portfolioId, entityId]
  );

  useEffect(() => {
    if (open) {
      fetchOptions(inputValue);
    }
  }, [open, inputValue, fetchOptions]);

  useEffect(() => {
    if (value && !selectedContact) {
      ApiClient.contacts
        .get(value)
        .then(contact => {
          setSelectedContact(contact);
        })
        .catch(() => {});
    } else if (!value) {
      setSelectedContact(null);
    }
  }, [value, selectedContact]);

  useEffect(() => {
    if (!entityId) {
      setSelectedContact(null);
      setOptions([]);
    }
  }, [entityId]);

  const handleChange = (_event: React.SyntheticEvent, newValue: OptionType | null) => {
    if (newValue && isAddNewOption(newValue)) {
      setCreateForm({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        title: ''
      });
      setCreateDialogOpen(true);
      return;
    }
    const contact = newValue as Contact | null;
    setSelectedContact(contact);
    onChange(contact?.id ?? null, contact);
  };

  const handleCreate = async () => {
    if (!createForm.first_name || !createForm.last_name) return;
    setCreating(true);
    try {
      const newContact = await ApiClient.contacts.create({
        scope_type: 'portfolio',
        portfolio_id: portfolioId,
        entity_id: entityId || undefined,
        first_name: createForm.first_name,
        last_name: createForm.last_name,
        email: createForm.email || undefined,
        phone: createForm.phone || undefined,
        title: createForm.title || undefined
      });
      setSelectedContact(newContact);
      onChange(newContact.id, newContact);
      setCreateDialogOpen(false);
      setOptions(prev => [newContact, ...prev]);
    } catch (_err) {
      // contact creation failed; picker stays open
    } finally {
      setCreating(false);
    }
  };

  const getContactLabel = (contact: Contact) => {
    return `${contact.first_name} ${contact.last_name}`;
  };

  const addNewOption: AddNewOption = {
    id: -1,
    first_name: '+ Add New',
    last_name: 'Contact',
    isAddNew: true
  };

  const allOptions: OptionType[] = [...options, addNewOption];

  return (
    <>
      <Autocomplete<OptionType, false, false, false>
        open={open}
        onOpen={() => setOpen(true)}
        onClose={() => setOpen(false)}
        value={selectedContact as OptionType | null}
        onChange={handleChange}
        inputValue={inputValue}
        onInputChange={(_event, newInputValue) => setInputValue(newInputValue)}
        options={allOptions}
        loading={loading}
        disabled={disabled || !entityId}
        size={size}
        getOptionLabel={option => {
          if (isAddNewOption(option)) return '+ Add New Contact';
          const contact = option as Contact;
          return getContactLabel(contact);
        }}
        isOptionEqualToValue={(option, val) => {
          if (isAddNewOption(option) || isAddNewOption(val)) return false;
          return (option as Contact).id === (val as Contact).id;
        }}
        filterOptions={x => x}
        renderOption={(props, option) => {
          if (isAddNewOption(option)) {
            return (
              <Box component="li" {...props} key="add-new-contact" sx={{ color: 'primary.main', fontWeight: 600 }}>
                <AddIcon sx={{ mr: 1, fontSize: 20 }} />
                Add New Contact
              </Box>
            );
          }
          const contact = option as Contact;
          return (
            <Box component="li" {...props} key={contact.id}>
              <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                <Typography variant="body2">
                  {contact.first_name} {contact.last_name}
                </Typography>
                {(contact.title || contact.email) && (
                  <Typography variant="caption" color="text.secondary">
                    {[contact.title, contact.email].filter(Boolean).join(' · ')}
                  </Typography>
                )}
              </Box>
            </Box>
          );
        }}
        renderInput={params => (
          <TextField
            {...params}
            label={label}
            placeholder="Search contacts..."
            InputProps={{
              ...params.InputProps,
              endAdornment: (
                <>
                  {loading ? <CircularProgress color="inherit" size={18} /> : null}
                  {params.InputProps.endAdornment}
                </>
              )
            }}
          />
        )}
      />

      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Add New Contact</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="First Name"
              required
              value={createForm.first_name}
              onChange={e => setCreateForm(prev => ({ ...prev, first_name: e.target.value }))}
              size="small"
              fullWidth
            />
            <TextField
              label="Last Name"
              required
              value={createForm.last_name}
              onChange={e => setCreateForm(prev => ({ ...prev, last_name: e.target.value }))}
              size="small"
              fullWidth
            />
            <TextField
              label="Title"
              value={createForm.title}
              onChange={e => setCreateForm(prev => ({ ...prev, title: e.target.value }))}
              size="small"
              fullWidth
            />
            <TextField
              label="Email"
              value={createForm.email}
              onChange={e => setCreateForm(prev => ({ ...prev, email: e.target.value }))}
              size="small"
              fullWidth
            />
            <TextField
              label="Phone"
              value={createForm.phone}
              onChange={e => setCreateForm(prev => ({ ...prev, phone: e.target.value }))}
              size="small"
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)} disabled={creating}>
            Cancel
          </Button>
          <Button
            onClick={handleCreate}
            variant="contained"
            disabled={creating || !createForm.first_name || !createForm.last_name}
          >
            {creating ? 'Creating...' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default EntityContactPicker;

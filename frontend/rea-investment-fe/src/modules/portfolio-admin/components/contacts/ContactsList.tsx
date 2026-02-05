import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Chip from '@mui/material/Chip';
import TextField from '@mui/material/TextField';
import InputAdornment from '@mui/material/InputAdornment';
import Skeleton from '@mui/material/Skeleton';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import Tooltip from '@mui/material/Tooltip';
import Alert from '@mui/material/Alert';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import SearchIcon from '@mui/icons-material/Search';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import PersonIcon from '@mui/icons-material/Person';
import ArchiveIcon from '@mui/icons-material/Archive';
import UnarchiveIcon from '@mui/icons-material/Unarchive';
import VerifiedUserIcon from '@mui/icons-material/VerifiedUser';

import { ApiClient } from '../../../../api';
import type { Contact, ContactScopeType } from '../../../../api';
import { useNotify } from '../../../../contexts/notifications/notifications';
import { ContactFormModal } from './ContactFormModal';

interface ContactsListProps {
  scopeType: ContactScopeType;
  scopeId: number;
  title?: string;
}

export const ContactsList: React.FC<ContactsListProps> = ({ scopeType, scopeId, title = 'Contacts' }) => {
  const queryClient = useQueryClient();
  const notify = useNotify();
  const [search, setSearch] = useState('');
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editContact, setEditContact] = useState<Contact | null>(null);
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; contact: Contact | null }>({
    open: false,
    contact: null
  });
  const [includeArchived, setIncludeArchived] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState<{ el: HTMLElement | null; contact: Contact | null }>({
    el: null,
    contact: null
  });

  const queryParams = {
    scope_type: scopeType,
    ...(scopeType === 'portfolio' && { portfolio_id: scopeId }),
    ...(scopeType === 'company' && { company_id: scopeId }),
    ...(scopeType === 'project' && { project_id: scopeId }),
    search: search || undefined,
    include_archived: includeArchived,
    limit: 100
  };

  const { data: contactsData, isLoading } = useQuery({
    queryKey: ['contacts', scopeType, scopeId, search, includeArchived],
    queryFn: () => ApiClient.contacts.list(queryParams),
    staleTime: 30 * 1000
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => ApiClient.contacts.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      notify('Contact deleted');
      setDeleteDialog({ open: false, contact: null });
    },
    onError: () => {
      notify('Failed to delete contact');
    }
  });

  const archiveMutation = useMutation({
    mutationFn: ({ id, archive }: { id: number; archive: boolean }) =>
      archive ? ApiClient.contacts.archive(id) : ApiClient.contacts.unarchive(id),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      notify(variables.archive ? 'Contact archived' : 'Contact restored');
    },
    onError: () => {
      notify('Failed to update contact');
    }
  });

  const contacts = contactsData?.items || [];

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, contact: Contact) => {
    event.stopPropagation();
    setMenuAnchor({ el: event.currentTarget, contact });
  };

  const handleMenuClose = () => {
    setMenuAnchor({ el: null, contact: null });
  };

  const handleEdit = () => {
    if (menuAnchor.contact) {
      setEditContact(menuAnchor.contact);
    }
    handleMenuClose();
  };

  const handleDelete = () => {
    if (menuAnchor.contact) {
      setDeleteDialog({ open: true, contact: menuAnchor.contact });
    }
    handleMenuClose();
  };

  const handleArchive = () => {
    if (menuAnchor.contact) {
      archiveMutation.mutate({ id: menuAnchor.contact.id, archive: !menuAnchor.contact.is_archived });
    }
    handleMenuClose();
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <TextField
            size="small"
            placeholder="Search contacts..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              )
            }}
            sx={{ width: 250 }}
          />
          <Chip
            label={includeArchived ? 'Showing archived' : 'Hide archived'}
            variant={includeArchived ? 'filled' : 'outlined'}
            size="small"
            onClick={() => setIncludeArchived(!includeArchived)}
            icon={includeArchived ? <UnarchiveIcon /> : <ArchiveIcon />}
          />
        </Box>
        <Button variant="contained" startIcon={<PersonAddIcon />} onClick={() => setIsAddOpen(true)}>
          Add Contact
        </Button>
      </Box>

      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>Phone</TableCell>
              <TableCell>Title</TableCell>
              <TableCell>Organization</TableCell>
              <TableCell>Tags</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              [1, 2, 3].map(i => (
                <TableRow key={i}>
                  <TableCell>
                    <Skeleton />
                  </TableCell>
                  <TableCell>
                    <Skeleton />
                  </TableCell>
                  <TableCell>
                    <Skeleton width={100} />
                  </TableCell>
                  <TableCell>
                    <Skeleton width={100} />
                  </TableCell>
                  <TableCell>
                    <Skeleton width={100} />
                  </TableCell>
                  <TableCell>
                    <Skeleton width={80} />
                  </TableCell>
                  <TableCell>
                    <Skeleton width={40} />
                  </TableCell>
                </TableRow>
              ))
            ) : contacts.length > 0 ? (
              contacts.map(contact => (
                <TableRow
                  key={contact.id}
                  sx={{
                    opacity: contact.is_archived ? 0.6 : 1,
                    backgroundColor: contact.is_archived ? 'action.hover' : 'inherit'
                  }}
                >
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <PersonIcon fontSize="small" color={contact.is_user ? 'primary' : 'action'} />
                      <Typography variant="body2">
                        {contact.first_name} {contact.last_name}
                      </Typography>
                      {contact.is_user && (
                        <Tooltip title="This contact is also a platform user">
                          <VerifiedUserIcon fontSize="small" color="success" />
                        </Tooltip>
                      )}
                      {contact.is_archived && <Chip label="Archived" size="small" variant="outlined" />}
                    </Box>
                  </TableCell>
                  <TableCell>{contact.email || '-'}</TableCell>
                  <TableCell>{contact.phone || '-'}</TableCell>
                  <TableCell>{contact.title || '-'}</TableCell>
                  <TableCell>{contact.organization || '-'}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                      {contact.tags?.slice(0, 3).map(tag => (
                        <Chip key={tag} label={tag} size="small" variant="outlined" />
                      ))}
                      {(contact.tags?.length || 0) > 3 && (
                        <Chip label={`+${contact.tags!.length - 3}`} size="small" variant="outlined" />
                      )}
                    </Box>
                  </TableCell>
                  <TableCell align="right">
                    <IconButton size="small" onClick={e => handleMenuOpen(e, contact)}>
                      <MoreVertIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography color="text.secondary" sx={{ py: 3 }}>
                    {search ? 'No contacts match your search' : 'No contacts yet. Add your first contact to get started.'}
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Menu anchorEl={menuAnchor.el} open={Boolean(menuAnchor.el)} onClose={handleMenuClose}>
        <MenuItem onClick={handleEdit}>
          <EditIcon fontSize="small" sx={{ mr: 1 }} />
          Edit
        </MenuItem>
        <MenuItem onClick={handleArchive}>
          {menuAnchor.contact?.is_archived ? (
            <>
              <UnarchiveIcon fontSize="small" sx={{ mr: 1 }} />
              Restore
            </>
          ) : (
            <>
              <ArchiveIcon fontSize="small" sx={{ mr: 1 }} />
              Archive
            </>
          )}
        </MenuItem>
        <MenuItem onClick={handleDelete} sx={{ color: 'error.main' }}>
          <DeleteIcon fontSize="small" sx={{ mr: 1 }} />
          Delete
        </MenuItem>
      </Menu>

      <Dialog open={deleteDialog.open} onClose={() => setDeleteDialog({ open: false, contact: null })}>
        <DialogTitle>Delete Contact</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to permanently delete{' '}
            <strong>
              {deleteDialog.contact?.first_name} {deleteDialog.contact?.last_name}
            </strong>
            ?
          </Typography>
          <Alert severity="warning" sx={{ mt: 2 }}>
            This action cannot be undone. Consider archiving instead if you may need this contact later.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false, contact: null })}>Cancel</Button>
          <Button
            variant="contained"
            color="error"
            onClick={() => deleteDialog.contact && deleteMutation.mutate(deleteDialog.contact.id)}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>

      <ContactFormModal
        open={isAddOpen}
        onClose={() => setIsAddOpen(false)}
        scopeType={scopeType}
        scopeId={scopeId}
      />

      <ContactFormModal
        open={!!editContact}
        onClose={() => setEditContact(null)}
        scopeType={scopeType}
        scopeId={scopeId}
        contact={editContact}
      />
    </Box>
  );
};

export default ContactsList;

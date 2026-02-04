import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import { ApiClient, type DocumentType } from '../../../../../../api';

type SubTab = 'document-types' | 'canonical-fields';

const ExtractionRegistry: React.FC = () => {
  const queryClient = useQueryClient();
  const [subTab, setSubTab] = useState<SubTab>('document-types');
  const [selectedDocType, setSelectedDocType] = useState<DocumentType | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newDocType, setNewDocType] = useState({ name: '', display_name: '', category: 'other' });

  const {
    data: documentTypes,
    isLoading: loadingDocTypes,
    error: docTypesError
  } = useQuery({
    queryKey: ['admin', 'extraction', 'document-types'],
    queryFn: () => ApiClient.admin.getDocumentTypes(false)
  });

  const { data: canonicalFields, isLoading: loadingFields } = useQuery({
    queryKey: ['admin', 'extraction', 'canonical-fields'],
    queryFn: () => ApiClient.admin.getCanonicalFields(false),
    enabled: subTab === 'canonical-fields'
  });

  const { data: schemaVersions, isLoading: loadingSchemas } = useQuery({
    queryKey: ['admin', 'extraction', 'schema-versions', selectedDocType?.id],
    queryFn: () => ApiClient.admin.getSchemaVersions(selectedDocType!.id),
    enabled: !!selectedDocType
  });

  const { data: promptTemplates, isLoading: loadingPrompts } = useQuery({
    queryKey: ['admin', 'extraction', 'prompt-templates', selectedDocType?.id],
    queryFn: () => ApiClient.admin.getPromptTemplates(selectedDocType!.id),
    enabled: !!selectedDocType
  });

  const createDocTypeMutation = useMutation({
    mutationFn: (data: typeof newDocType) => ApiClient.admin.createDocumentType(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'extraction', 'document-types'] });
      setCreateDialogOpen(false);
      setNewDocType({ name: '', display_name: '', category: 'other' });
    }
  });

  const activateSchemaMutation = useMutation({
    mutationFn: (versionId: number) => ApiClient.admin.activateSchemaVersion(versionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'extraction', 'schema-versions', selectedDocType?.id] });
    }
  });

  const activatePromptMutation = useMutation({
    mutationFn: (templateId: number) => ApiClient.admin.activatePromptTemplate(templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'extraction', 'prompt-templates', selectedDocType?.id] });
    }
  });

  const handleCreateDocType = () => {
    createDocTypeMutation.mutate(newDocType);
  };

  if (docTypesError) {
    return <Alert severity="error">Failed to load extraction registry. Admin access required.</Alert>;
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">Extraction Registry</Typography>
        {subTab === 'document-types' && (
          <Button variant="contained" onClick={() => setCreateDialogOpen(true)}>
            Add Document Type
          </Button>
        )}
      </Box>

      <Tabs value={subTab} onChange={(_, v) => setSubTab(v)} sx={{ mb: 2 }}>
        <Tab value="document-types" label="Document Types" />
        <Tab value="canonical-fields" label="Canonical Fields" />
      </Tabs>

      {subTab === 'document-types' && (
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Paper sx={{ width: '40%', p: 2 }}>
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
              Document Types
            </Typography>
            {loadingDocTypes ? (
              <CircularProgress size={24} />
            ) : (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Name</TableCell>
                      <TableCell>Category</TableCell>
                      <TableCell>Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {documentTypes?.map(dt => (
                      <TableRow
                        key={dt.id}
                        hover
                        selected={selectedDocType?.id === dt.id}
                        onClick={() => setSelectedDocType(dt)}
                        sx={{ cursor: 'pointer' }}
                      >
                        <TableCell>{dt.display_name}</TableCell>
                        <TableCell>{dt.category}</TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={dt.is_active ? 'Active' : 'Inactive'}
                            color={dt.is_active ? 'success' : 'default'}
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Paper>

          <Paper sx={{ width: '60%', p: 2 }}>
            {selectedDocType ? (
              <>
                <Typography variant="subtitle1" sx={{ mb: 2 }}>
                  {selectedDocType.display_name} Configuration
                </Typography>

                <Accordion defaultExpanded>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography>Schema Versions</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    {loadingSchemas ? (
                      <CircularProgress size={24} />
                    ) : (
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Version</TableCell>
                            <TableCell>Fields</TableCell>
                            <TableCell>Notes</TableCell>
                            <TableCell>Actions</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {schemaVersions?.map(sv => (
                            <TableRow key={sv.id}>
                              <TableCell>
                                v{sv.version}
                                {sv.is_active && <CheckCircleIcon color="success" sx={{ ml: 1, fontSize: 16 }} />}
                              </TableCell>
                              <TableCell>{sv.fields?.length || 0}</TableCell>
                              <TableCell>{sv.notes || '-'}</TableCell>
                              <TableCell>
                                {!sv.is_active && (
                                  <Button
                                    size="small"
                                    onClick={() => activateSchemaMutation.mutate(sv.id)}
                                    disabled={activateSchemaMutation.isPending}
                                  >
                                    Activate
                                  </Button>
                                )}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    )}
                  </AccordionDetails>
                </Accordion>

                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography>Prompt Templates</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    {loadingPrompts ? (
                      <CircularProgress size={24} />
                    ) : (
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Version</TableCell>
                            <TableCell>Model</TableCell>
                            <TableCell>Notes</TableCell>
                            <TableCell>Actions</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {promptTemplates?.map(pt => (
                            <TableRow key={pt.id}>
                              <TableCell>
                                v{pt.version}
                                {pt.is_active && <CheckCircleIcon color="success" sx={{ ml: 1, fontSize: 16 }} />}
                              </TableCell>
                              <TableCell>{pt.model_name}</TableCell>
                              <TableCell>{pt.notes || '-'}</TableCell>
                              <TableCell>
                                {!pt.is_active && (
                                  <Button
                                    size="small"
                                    onClick={() => activatePromptMutation.mutate(pt.id)}
                                    disabled={activatePromptMutation.isPending}
                                  >
                                    Activate
                                  </Button>
                                )}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    )}
                  </AccordionDetails>
                </Accordion>
              </>
            ) : (
              <Typography color="text.secondary">Select a document type to view configuration</Typography>
            )}
          </Paper>
        </Box>
      )}

      {subTab === 'canonical-fields' && (
        <Paper sx={{ p: 2 }}>
          {loadingFields ? (
            <CircularProgress size={24} />
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Display Name</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {canonicalFields?.map(field => (
                    <TableRow key={field.id}>
                      <TableCell>{field.name}</TableCell>
                      <TableCell>{field.display_name}</TableCell>
                      <TableCell>{field.field_type}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={field.is_active ? 'Active' : 'Inactive'}
                          color={field.is_active ? 'success' : 'default'}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>
      )}

      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)}>
        <DialogTitle>Add Document Type</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Name (internal)"
            fullWidth
            value={newDocType.name}
            onChange={e => setNewDocType({ ...newDocType, name: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Display Name"
            fullWidth
            value={newDocType.display_name}
            onChange={e => setNewDocType({ ...newDocType, display_name: e.target.value })}
          />
          <TextField
            margin="dense"
            label="Category"
            fullWidth
            value={newDocType.category}
            onChange={e => setNewDocType({ ...newDocType, category: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreateDocType}
            variant="contained"
            disabled={createDocTypeMutation.isPending || !newDocType.name || !newDocType.display_name}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ExtractionRegistry;

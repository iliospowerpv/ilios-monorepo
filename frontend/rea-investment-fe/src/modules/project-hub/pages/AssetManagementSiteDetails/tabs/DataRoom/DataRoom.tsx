import React, { useCallback, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import AddIcon from '@mui/icons-material/Add';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';

import type { AssetManagementSiteDetailsTabProps } from '../types';
import { useFocusHighlight } from '../../../../../../hooks/useFocusHighlight';
import { ApiClient, DiligenceDocument, DiligenceItem } from '../../../../../../api';
import SearchAndActions from '../../../../../../components/common/tables/components/SearchAndActions/SearchAndActions';
import { useNotify } from '../../../../../../contexts/notifications/notifications';
import RecursiveAccordion from '../../../../../../modules/due-diligence/pages/Site/tabs/Diligence/components/RecursiveAccordion/RecursiveAccordion';

const siteDiligenceQuery = (siteId: number, enabled = true) => ({
  queryKey: ['site', 'diligence', { siteId }],
  queryFn: () => ApiClient.dueDiligence.getDocuments(siteId),
  enabled: enabled
});

interface SectionOption {
  id: number;
  name: string;
}

export const DataRoom: React.FC<AssetManagementSiteDetailsTabProps> = ({ siteDetails }) => {
  const { siteId } = useParams<{ siteId: string }>();
  const { focusState } = useFocusHighlight();
  const queryClient = useQueryClient();
  const notify = useNotify();

  const numericSiteId = siteId ? Number(siteId) : siteDetails.id;
  const isValidId = !!numericSiteId && Number.isSafeInteger(numericSiteId);

  const {
    data,
    isLoading,
    isFetching,
    error,
    refetch
  } = useQuery(siteDiligenceQuery(isValidId ? numericSiteId : -1, isValidId));

  const [searchTerm, setSearchTerm] = useState('');
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [newDocName, setNewDocName] = useState('');
  const [newDocDescription, setNewDocDescription] = useState('');
  const [selectedSectionId, setSelectedSectionId] = useState<number | ''>('');

  const extractSections = useCallback((items: DiligenceItem[]): SectionOption[] => {
    const sections: SectionOption[] = [];
    const traverse = (sectionItems: DiligenceItem[]) => {
      sectionItems.forEach(item => {
        if (item.documents_count >= 0) {
          const sectionId = (item as any).id;
          if (sectionId) {
            sections.push({ id: sectionId, name: item.name });
          }
        }
        if (item.related_sections?.length) {
          traverse(item.related_sections);
        }
      });
    };
    traverse(items);
    return sections;
  }, []);

  const sections = data?.items ? extractSections(data.items) : [];

  const createDocMutation = useMutation({
    mutationFn: () =>
      ApiClient.dueDiligence.createCustomDocument(
        numericSiteId,
        selectedSectionId as number,
        newDocName,
        newDocDescription || undefined
      ),
    onSuccess: () => {
      notify('Document created successfully');
      queryClient.invalidateQueries({ queryKey: ['site', 'diligence', { siteId: numericSiteId }] });
      setAddDialogOpen(false);
      setNewDocName('');
      setNewDocDescription('');
      setSelectedSectionId('');
      refetch();
    },
    onError: (error: any) => {
      notify(error?.response?.data?.detail || 'Failed to create document');
    }
  });

  const handleAddDocument = () => {
    if (!newDocName.trim() || !selectedSectionId) {
      notify('Please fill in all required fields');
      return;
    }
    createDocMutation.mutate();
  };

  const handleSearch = (value: string) => {
    setSearchTerm(value);
  };

  const handleRefresh = () => {
    refetch();
  };

  const filterSections = useCallback((items: DiligenceItem[], search: string): DiligenceItem[] => {
    return items
      ?.map((section: DiligenceItem) => {
        const matchingDocuments = section.documents.filter((doc: DiligenceDocument) =>
          doc.name.toLowerCase().includes(search.toLowerCase())
        );

        const filteredRelatedSections = filterSections(section.related_sections, search);

        if (matchingDocuments.length > 0 || filteredRelatedSections?.length > 0) {
          return {
            ...section,
            documents: matchingDocuments,
            documents_count: matchingDocuments.length,
            related_sections: filteredRelatedSections
          };
        }

        return null;
      })
      .filter((section): section is DiligenceItem => section !== null);
  }, []);

  if (error) {
    return (
      <Box>
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to load data room content. Please try again.
        </Alert>
      </Box>
    );
  }

  const filterResult = data?.items && filterSections(data.items, searchTerm);

  return (
    <Box>
      {focusState.notFoundMessage && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {focusState.notFoundMessage}
        </Alert>
      )}

      <Box display="flex" alignItems="center" gap={1} mb={3}>
        <FolderOpenIcon color="primary" />
        <Typography variant="h5" sx={{ fontWeight: 500 }}>
          Data Room
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
          {siteDetails.name}
        </Typography>
      </Box>

      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <SearchAndActions
          showSearch={true}
          showAdd={false}
          reversOrder={false}
          searchPlaceholder="Search documents..."
          onSearch={handleSearch}
        />
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setAddDialogOpen(true)}>
          Add Document
        </Button>
      </Box>

      <Dialog open={addDialogOpen} onClose={() => setAddDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add New Document</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Document Name"
              value={newDocName}
              onChange={e => setNewDocName(e.target.value)}
              fullWidth
              required
            />
            <TextField
              label="Description (optional)"
              value={newDocDescription}
              onChange={e => setNewDocDescription(e.target.value)}
              fullWidth
              multiline
              rows={2}
            />
            <FormControl fullWidth required>
              <InputLabel>Section</InputLabel>
              <Select
                value={selectedSectionId}
                label="Section"
                onChange={e => setSelectedSectionId(e.target.value as number)}
              >
                {sections.map(section => (
                  <MenuItem key={section.id} value={section.id}>
                    {section.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleAddDocument} variant="contained" disabled={createDocMutation.isPending}>
            {createDocMutation.isPending ? 'Creating...' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {isLoading || isFetching ? (
        <Box display="flex" alignItems="center" justifyContent="center" mt="40px">
          <CircularProgress color="inherit" size={40} />
        </Box>
      ) : searchTerm && !filterResult?.length ? (
        <Box display="flex" alignItems="center" justifyContent="center" mt="40px">
          <Typography variant="body1">No documents found matching your search</Typography>
        </Box>
      ) : filterResult?.length ? (
        <RecursiveAccordion items={filterResult} forceExpanded={!!searchTerm} onRefresh={handleRefresh} />
      ) : (
        <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" mt="40px">
          <FolderOpenIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
          <Typography variant="body1" color="text.secondary">
            No documents in the data room yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Click "Add Document" to get started
          </Typography>
        </Box>
      )}

      {focusState.focusId && focusState.focusType === 'document' && (
        <Typography variant="body2" sx={{ mt: 2, fontStyle: 'italic', color: 'text.secondary' }}>
          Navigated to document ID: {focusState.focusId}
        </Typography>
      )}
    </Box>
  );
};

export default DataRoom;

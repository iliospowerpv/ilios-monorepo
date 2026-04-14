import React, { useCallback, useState } from 'react';
import { useParams } from 'react-router-dom';
import { siteDiligenceQuery } from '../../loader';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import AddIcon from '@mui/icons-material/Add';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import { SearchableSelect } from '../../../../../../components/common/SearchableSelect/SearchableSelect';

import RecursiveAccordion from './components/RecursiveAccordion/RecursiveAccordion';
import { ApiClient, DiligenceDocument, DiligenceItem } from '../../../../../../api';
import SearchAndActions from '../../../../../../components/common/tables/components/SearchAndActions/SearchAndActions';
import { useNotify } from '../../../../../../contexts/notifications/notifications';

const LoadingComponent: React.FC = () => (
  <Box display="flex" alignItems="center" justifyContent="center" mt="40px">
    <CircularProgress color="inherit" size={40} />
  </Box>
);

const NoItemsComponent: React.FC = () => (
  <Box display="flex" alignItems="center" justifyContent="center" mt="40px">
    <Typography variant="body1">No results found for the given input</Typography>
  </Box>
);

interface SectionOption {
  id: number;
  name: string;
}

const DiligenceList: React.FC = () => {
  const { siteId } = useParams();
  const isValidId = !!siteId && Number.isSafeInteger(Number.parseInt(siteId));
  const queryClient = useQueryClient();
  const notify = useNotify();
  const {
    data,
    isLoading: isLoadingDiligence,
    isFetching: isFetchingDiligence,
    error: diligenceDetailsLoadingError,
    refetch
  } = useQuery(siteDiligenceQuery(isValidId ? Number.parseInt(siteId) : -1));
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
        Number(siteId),
        selectedSectionId as number,
        newDocName,
        newDocDescription || undefined
      ),
    onSuccess: () => {
      notify('Document created successfully');
      queryClient.invalidateQueries({ queryKey: ['site', 'diligence', { siteId: Number(siteId) }] });
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

  const filterSections = useCallback((sections: DiligenceItem[], search: string): any => {
    return sections
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
      .filter(section => section !== null);
  }, []);

  if (diligenceDetailsLoadingError) return null;

  const filterResult = data?.items && filterSections(data.items, searchTerm);

  return (
    <>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <SearchAndActions
          showSearch={true}
          showAdd={false}
          reversOrder={false}
          searchPlaceholder="Search"
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
            <SearchableSelect
              options={sections.map(section => ({
                label: section.name,
                value: section.id
              }))}
              value={selectedSectionId || null}
              onChange={val => setSelectedSectionId(val as number)}
              label="Section"
              required
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleAddDocument} variant="contained" disabled={createDocMutation.isPending}>
            {createDocMutation.isPending ? 'Creating...' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {isLoadingDiligence || isFetchingDiligence ? (
        <LoadingComponent />
      ) : searchTerm && !filterResult?.length ? (
        <NoItemsComponent />
      ) : filterResult?.length ? (
        <RecursiveAccordion items={filterResult} forceExpanded={!!searchTerm} onRefresh={handleRefresh} />
      ) : null}
    </>
  );
};

export default DiligenceList;

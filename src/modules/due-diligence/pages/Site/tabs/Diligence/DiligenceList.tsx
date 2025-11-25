import React, { useCallback, useState } from 'react';
import { useParams } from 'react-router-dom';
import { siteDiligenceQuery } from '../../loader';
import { useQuery } from '@tanstack/react-query';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

import RecursiveAccordion from './components/RecursiveAccordion/RecursiveAccordion';
import { DiligenceDocument, DiligenceItem } from '../../../../../../api';
import SearchAndActions from '../../../../../../components/common/tables/components/SearchAndActions/SearchAndActions';

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

const DiligenceList: React.FC = () => {
  const { siteId } = useParams();
  const isValidId = !!siteId && Number.isSafeInteger(Number.parseInt(siteId));
  const {
    data,
    isLoading: isLoadingDiligence,
    isFetching: isFetchingDiligence,
    error: diligenceDetailsLoadingError
  } = useQuery(siteDiligenceQuery(isValidId ? Number.parseInt(siteId) : -1));
  const [searchTerm, setSearchTerm] = useState('');

  const handleSearch = (value: string) => {
    setSearchTerm(value);
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
      <SearchAndActions
        showSearch={true}
        showAdd={false}
        reversOrder={false}
        searchPlaceholder="Search"
        onSearch={handleSearch}
      />
      {isLoadingDiligence || isFetchingDiligence ? (
        <LoadingComponent />
      ) : searchTerm && !filterResult?.length ? (
        <NoItemsComponent />
      ) : filterResult?.length ? (
        <RecursiveAccordion items={filterResult} forceExpanded={!!searchTerm} />
      ) : null}
    </>
  );
};

export default DiligenceList;

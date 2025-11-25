import React from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Link from '@mui/material/Link';
import CircularProgress from '@mui/material/CircularProgress';
import { Autocomplete, TextField } from '@mui/material';
import { AutocompleteRenderInputParams } from '@mui/material/Autocomplete';
import { AxiosError } from 'axios';
import { useQuery } from '@tanstack/react-query';

import { ApiClient, AgreementType, AgreementTerm } from '../../../../../../../../api';
import { useNotify } from '../../../../../../../../contexts/notifications/notifications';

interface TermsAndValuesListProps {
  companyId: number;
  siteId: number;
}

interface TermComponentProps {
  term: AgreementTerm;
}

const TermComponent: React.FC<TermComponentProps> = ({ term }) => {
  return (
    <Box sx={{ marginBottom: '16px' }}>
      <Typography variant="h6" sx={{ fontSize: '14px', fontWeight: 600, py: '8px' }}>
        {term.name}
      </Typography>
      <Typography variant="body2" sx={{ fontSize: '14px', color: theme => theme.palette.text.secondary }}>
        {term.value || 'N/A'}
      </Typography>
    </Box>
  );
};

const TermsAndValuesList: React.FC<TermsAndValuesListProps> = ({ siteId, companyId }) => {
  const notify = useNotify();
  const navigate = useNavigate();
  const [selectedType, setSelectedType] = React.useState<AgreementType | null>(null);

  const {
    data: typeData,
    isLoading: isLoadingTypeData,
    isFetching: isFetchingTypeData,
    error
  } = useQuery({
    queryFn: async () => {
      return ApiClient.dueDiligence.getAgreementTypes(siteId);
    },
    queryKey: ['agreement-type', { siteId }]
  });

  const {
    data: termData,
    isLoading: isLoadingTermData,
    isFetching: isFetchingTermData
  } = useQuery({
    queryFn: async () => {
      if (selectedType?.id) {
        return ApiClient.dueDiligence.getAgreementTerms(siteId, selectedType.id);
      }
      return { items: [] };
    },
    queryKey: ['agreement-term', { siteId, typeId: selectedType?.id }],
    enabled: !!selectedType
  });

  React.useEffect(() => {
    if (error && error instanceof AxiosError) notify(error.message);
  }, [error, notify]);

  React.useEffect(() => {
    if (typeData?.items[0]) {
      setSelectedType(typeData?.items[0]);
    }
  }, [typeData, isLoadingTypeData]);

  const AgreementTerms =
    selectedType && termData
      ? termData?.items?.map((term: AgreementTerm) => <TermComponent key={term.name} term={term} />)
      : null;

  const inputRenderer = (params: AutocompleteRenderInputParams) => (
    <TextField
      {...params}
      placeholder="Select an agreement type"
      variant="outlined"
      InputProps={{
        ...params.InputProps,
        endAdornment: (
          <React.Fragment>
            {isLoadingTypeData || isFetchingTypeData ? <CircularProgress color="inherit" size={20} /> : undefined}
            {params.InputProps.endAdornment}
          </React.Fragment>
        )
      }}
    />
  );

  const onViewDetails = () => {
    navigate(`/due-diligence/companies/${companyId}/sites/${siteId}/due-diligence/${selectedType?.id}`);
  };

  if (isLoadingTypeData || !typeData) return null;

  return (
    <>
      <Box sx={{ marginBottom: '16px' }} data-testid="list__component">
        <Autocomplete
          value={selectedType}
          options={typeData?.items || []}
          clearOnBlur
          getOptionLabel={option => option.name}
          loading={isLoadingTypeData || isFetchingTypeData}
          getOptionKey={option => option.id}
          sx={{ display: 'inline-block', minWidth: '300px' }}
          renderInput={inputRenderer}
          onChange={(event, newValue) => {
            setSelectedType(newValue);
          }}
        />
      </Box>
      {selectedType && (
        <Box sx={{ border: '1px solid #0000003B', padding: '16px', marginBottom: '16px' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <Typography variant="h6">{selectedType?.name}</Typography>
            <Link component="button" variant="body2" underline="hover" fontWeight={600} onClick={onViewDetails}>
              View Details
            </Link>
          </Box>
          <Box>
            {isLoadingTermData || isFetchingTermData ? (
              <Typography variant="body2" sx={{ fontSize: '14px', color: theme => theme.palette.text.secondary }}>
                Loading...
              </Typography>
            ) : (
              AgreementTerms
            )}
          </Box>
        </Box>
      )}
    </>
  );
};

export default TermsAndValuesList;

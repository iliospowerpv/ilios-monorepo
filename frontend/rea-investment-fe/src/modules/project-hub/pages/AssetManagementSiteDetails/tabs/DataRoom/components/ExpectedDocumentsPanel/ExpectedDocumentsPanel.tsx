import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Chip from '@mui/material/Chip';
import Collapse from '@mui/material/Collapse';
import Paper from '@mui/material/Paper';
import Tooltip from '@mui/material/Tooltip';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ChecklistRtlIcon from '@mui/icons-material/ChecklistRtl';

import { ApiClient } from '../../../../../../../../api';

interface ExpectedDocumentsPanelProps {
  siteId: number;
}

export const ExpectedDocumentsPanel: React.FC<ExpectedDocumentsPanelProps> = ({ siteId }) => {
  const [expanded, setExpanded] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['site', 'expected-documents', { siteId }],
    queryFn: () => ApiClient.dueDiligence.getExpectedDocuments(siteId),
    enabled: !!siteId && Number.isSafeInteger(siteId)
  });

  const sections = data?.items ?? [];
  const totalExpected = sections.reduce((sum, section) => sum + section.expected_documents.length, 0);

  return (
    <Paper elevation={0} sx={{ p: 2, mb: 3, border: '1px solid #E0E0E0' }}>
      <Box
        display="flex"
        alignItems="center"
        justifyContent="space-between"
        sx={{ cursor: 'pointer' }}
        onClick={() => setExpanded(prev => !prev)}
      >
        <Box display="flex" alignItems="center" gap={1}>
          <ChecklistRtlIcon color="primary" />
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Expected Documents
          </Typography>
          {!isLoading && !error && (
            <Typography variant="body2" color="text.secondary">
              {totalExpected} across {sections.length} stages
            </Typography>
          )}
        </Box>
        <IconButton size="small" aria-label={expanded ? 'Collapse expected documents' : 'Expand expected documents'}>
          {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        </IconButton>
      </Box>

      <Collapse in={expanded} timeout="auto" unmountOnExit>
        <Box mt={2}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            A read-only reference of the documents expected at each stage. This list is a guide only and does not create
            documents.
          </Typography>

          {isLoading ? (
            <Box display="flex" alignItems="center" justifyContent="center" py={3}>
              <CircularProgress size={28} />
            </Box>
          ) : error ? (
            <Alert severity="error">Failed to load the expected documents reference. Please try again.</Alert>
          ) : sections.length === 0 ? (
            <Alert severity="info">No expected documents are defined for this project.</Alert>
          ) : (
            <Stack spacing={2}>
              {sections.map(section => (
                <Box key={section.section_key}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                    {section.section_name}
                  </Typography>
                  <Stack spacing={0.75}>
                    {section.expected_documents.map(doc => (
                      <Box key={doc.kind} display="flex" alignItems="flex-start" gap={1}>
                        <Chip
                          size="small"
                          label={doc.required ? 'Required' : 'Optional'}
                          color={doc.required ? 'primary' : 'default'}
                          variant={doc.required ? 'filled' : 'outlined'}
                          sx={{ mt: 0.25 }}
                        />
                        <Box>
                          {doc.description ? (
                            <Tooltip title={doc.description} placement="top-start">
                              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                {doc.name}
                              </Typography>
                            </Tooltip>
                          ) : (
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {doc.name}
                            </Typography>
                          )}
                          {doc.description && (
                            <Typography variant="caption" color="text.secondary">
                              {doc.description}
                            </Typography>
                          )}
                        </Box>
                      </Box>
                    ))}
                  </Stack>
                </Box>
              ))}
            </Stack>
          )}
        </Box>
      </Collapse>
    </Paper>
  );
};

export default ExpectedDocumentsPanel;

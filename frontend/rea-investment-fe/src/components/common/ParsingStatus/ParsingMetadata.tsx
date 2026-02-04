import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import { formatCharCount } from '../../../utils/parsing';

interface ParsingMetadataProps {
  charCount?: number;
  wordCount?: number;
  pageCount?: number;
  correlationId?: string;
  runId?: number;
  showDebugInfo?: boolean;
}

const ParsingMetadata: React.FC<ParsingMetadataProps> = ({
  charCount,
  wordCount,
  pageCount,
  correlationId,
  runId,
  showDebugInfo = false,
}) => {
  const hasMetadata = charCount || wordCount || pageCount;
  const hasDebugInfo = correlationId || runId;

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  if (!hasMetadata && !hasDebugInfo) return null;

  return (
    <Box sx={{ mb: 2 }}>
      {hasMetadata && (
        <Box display="flex" gap={1} flexWrap="wrap" mb={1}>
          {pageCount && (
            <Chip
              size="small"
              variant="outlined"
              label={`${pageCount} pages`}
              sx={{ fontSize: '12px' }}
            />
          )}
          {charCount && (
            <Chip
              size="small"
              variant="outlined"
              label={`${formatCharCount(charCount)} chars`}
              sx={{ fontSize: '12px' }}
            />
          )}
          {wordCount && (
            <Chip
              size="small"
              variant="outlined"
              label={`${formatCharCount(wordCount)} words`}
              sx={{ fontSize: '12px' }}
            />
          )}
        </Box>
      )}
      
      {showDebugInfo && hasDebugInfo && (
        <Accordion sx={{ mt: 1, boxShadow: 'none', border: '1px solid #e0e0e0' }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="body2" color="text.secondary">
              Debug Details
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Box sx={{ fontFamily: 'monospace', fontSize: '12px' }}>
              {runId && (
                <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                  <Typography variant="body2" color="text.secondary" sx={{ minWidth: '100px' }}>
                    Run ID:
                  </Typography>
                  <Typography variant="body2">{runId}</Typography>
                </Box>
              )}
              {correlationId && (
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body2" color="text.secondary" sx={{ minWidth: '100px' }}>
                    Correlation ID:
                  </Typography>
                  <Typography variant="body2" sx={{ wordBreak: 'break-all' }}>
                    {correlationId}
                  </Typography>
                  <Tooltip title="Copy">
                    <IconButton size="small" onClick={() => copyToClipboard(correlationId)}>
                      <ContentCopyIcon sx={{ fontSize: '14px' }} />
                    </IconButton>
                  </Tooltip>
                </Box>
              )}
            </Box>
          </AccordionDetails>
        </Accordion>
      )}
    </Box>
  );
};

export default ParsingMetadata;

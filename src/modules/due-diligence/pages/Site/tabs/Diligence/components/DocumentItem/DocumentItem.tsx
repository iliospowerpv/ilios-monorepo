import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Grid from '@mui/material/Grid';
import Tooltip from '@mui/material/Tooltip';

import Assignee from '../Assignee/Assignee';
import { DiligenceDocument } from '../../../../../../../../api';

interface DocumentItemProps {
  document: DiligenceDocument;
}

const DocumentItem: React.FC<DocumentItemProps> = ({ document }) => {
  const navigate = useNavigate();
  const { siteId, companyId } = useParams();

  const filesCount = (item: number) => {
    switch (item) {
      case 0:
        return 'No Files Yet';
      case 1:
        return '1 File';
      default:
        return `${item} Files`;
    }
  };

  return (
    <Box
      data-testid="document-item__component"
      component="button"
      onClick={() => navigate(`/due-diligence/companies/${companyId}/sites/${siteId}/due-diligence/${document.id}`)}
      sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '8px',
        minHeight: '80px',
        width: '100%',
        borderRight: 0,
        borderTop: 0,
        borderLeft: 0,
        borderBottom: '1px solid #E0E0E0',
        background: 'rgb(255, 255, 255)',
        textAlign: 'left',
        fontSize: '16px',
        lineHeight: '24px',
        cursor: 'pointer',
        fontFamily: 'Lato, sans-serif',
        transition:
          'background-color 250ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 250ms cubic-bezier(0.4, 0, 0.2, 1), border-color 250ms cubic-bezier(0.4, 0, 0.2, 1), color 250ms cubic-bezier(0.4, 0, 0.2, 1);',
        '&:last-child': {
          borderBottom: 0
        },
        '&:hover': {
          background: 'rgb(240, 240, 240)'
        }
      }}
    >
      <Box width="40%" ml="auto" display="inline" gap="12px">
        <Box component="span" marginInlineEnd="12px">
          {document.name}
        </Box>
        {document.ai_supported && (
          <Tooltip
            title="Supports AI parsing"
            componentsProps={{
              tooltip: { sx: { bgcolor: '#121212', borderRadius: '4px' } },
              popper: {
                modifiers: [
                  {
                    name: 'offset',
                    options: {
                      offset: [72, -8]
                    }
                  }
                ]
              }
            }}
          >
            <Chip
              label="AI"
              size="small"
              sx={{
                cursor: 'default',
                height: '22px',
                fontWeight: 500,
                fontSize: '13px',
                lineHeight: '16px',
                color: '#FFFFFF',
                background: 'linear-gradient(245.75deg, #456CF3 7.17%, #8D4BE9 89.9%)'
              }}
            />
          </Tooltip>
        )}
      </Box>
      <Box width="15%">{filesCount(document.files_count)}</Box>
      <Box width="40%" minWidth="265px" height="100%" mr="auto">
        <Grid container spacing={2} justifyContent="flex-start" alignItems="center" wrap="nowrap">
          <Grid item xs={4} ml="auto">
            {document.status && (
              <Chip
                label={document.status}
                size="small"
                sx={theme => ({
                  color: theme.palette.primary.main,
                  background: '#F4E998',
                  minWidth: '75px'
                })}
              />
            )}
          </Grid>
          <Grid item mr="auto">
            <Assignee user={document.assignee} />
          </Grid>
          <Grid item ml="auto">
            <Button
              variant="outlined"
              sx={{ width: '120px', height: '32px', padding: '0', fontWeight: '500' }}
              onClick={() => {
                navigate(`/due-diligence/companies/${companyId}/sites/${siteId}/due-diligence/${document.id}`);
              }}
            >
              Open
            </Button>
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default DocumentItem;

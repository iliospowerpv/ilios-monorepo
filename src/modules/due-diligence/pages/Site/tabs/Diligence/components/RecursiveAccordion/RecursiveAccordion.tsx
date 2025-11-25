import React from 'react';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import Typography from '@mui/material/Typography';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown';
import Box from '@mui/material/Box';

import ProgressBar from '../ProgressBar/ProgressBar';
import DocumentItem from '../DocumentItem/DocumentItem';
import { DiligenceItem } from '../../../../../../../../api';

interface RecursiveAccordionProps {
  items: DiligenceItem[] | undefined;
  forceExpanded?: boolean;
}

const ManagedAccordion: React.FC<{ children: NonNullable<React.ReactNode>; forceExpanded?: boolean }> = ({
  children,
  forceExpanded
}) => {
  const [expanded, setExpanded] = React.useState(true);

  React.useEffect(() => {
    if (forceExpanded) {
      setExpanded(true);
    }
  }, [forceExpanded]);

  return (
    <Accordion
      data-testid="accordion-item__component"
      sx={{ boxShadow: 'none', border: '1px solid #E0E0E0', marginBottom: '20px' }}
      expanded={expanded}
      onChange={() => setExpanded(isExpanded => !isExpanded)}
    >
      {children}
    </Accordion>
  );
};

const RecursiveAccordion: React.FC<RecursiveAccordionProps> = ({ items, forceExpanded }) => {
  return (
    <>
      {items?.map(item => (
        <ManagedAccordion forceExpanded={forceExpanded} key={item.name}>
          <AccordionSummary
            expandIcon={<ArrowDropDownIcon />}
            aria-controls="panel2-content"
            id="panel2-header"
            sx={{
              flexDirection: 'row-reverse',
              height: '54px',
              borderBottom: '1px solid #E0E0E0',
              backgroundColor: 'rgba(0, 0, 0, 0.04)'
            }}
          >
            <Box width="100%" display="flex" alignItems="center" justifyContent="space-between">
              <Typography sx={{ fontWeight: 'bold', width: '50%' }}>
                {item.name} {!!item.documents_count && `(${item.documents_count})`}
              </Typography>
              {typeof item.completed_tasks_percentage === 'number' ? (
                <Box marginLeft="16px" flexGrow={1} width="50%" minWidth="100px" maxWidth="320px">
                  <ProgressBar value={item.completed_tasks_percentage} />
                </Box>
              ) : null}
            </Box>
          </AccordionSummary>
          <AccordionDetails sx={{ padding: '0' }}>
            {item.documents.map(document => (
              <DocumentItem key={`doc+${document.id}`} document={document} />
            ))}
            {!!item?.related_sections.length && (
              <Box sx={{ padding: '16px' }}>
                <RecursiveAccordion forceExpanded={forceExpanded} items={item.related_sections} />
              </Box>
            )}
          </AccordionDetails>
        </ManagedAccordion>
      ))}
    </>
  );
};

export default RecursiveAccordion;

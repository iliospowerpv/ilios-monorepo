import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import Typography from '@mui/material/Typography';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown';
import Box from '@mui/material/Box';
import { DragDropContext, Droppable, Draggable, DropResult } from 'react-beautiful-dnd';

import ProgressBar from '../ProgressBar/ProgressBar';
import DocumentItem from '../DocumentItem/DocumentItem';
import { ApiClient, DiligenceDocument, DiligenceItem } from '../../../../../../../../api';
import { useNotify } from '../../../../../../../../contexts/notifications/notifications';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';

interface RecursiveAccordionProps {
  items: DiligenceItem[] | undefined;
  forceExpanded?: boolean;
  onRefresh?: () => void;
  onDocumentClick?: (document: DiligenceDocument) => void;
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
      sx={theme => ({ boxShadow: 'none', border: `1px solid ${theme.palette.divider}`, marginBottom: '20px' })}
      expanded={expanded}
      onChange={() => setExpanded(isExpanded => !isExpanded)}
    >
      {children}
    </Accordion>
  );
};

interface SortableDocumentListProps {
  documents: DiligenceDocument[];
  sectionName: string;
  onRefresh?: () => void;
  onDocumentClick?: (document: DiligenceDocument) => void;
}

const SortableDocumentList: React.FC<SortableDocumentListProps> = ({
  documents: initialDocuments,
  sectionName,
  onRefresh,
  onDocumentClick
}) => {
  const { siteId } = useParams();
  const notify = useNotify();
  const [documents, setDocuments] = useState<DiligenceDocument[]>(initialDocuments);
  const previousDocumentsRef = React.useRef<DiligenceDocument[]>(initialDocuments);

  React.useEffect(() => {
    setDocuments(initialDocuments);
    previousDocumentsRef.current = initialDocuments;
  }, [initialDocuments]);

  const reorderMutation = useMutation({
    mutationFn: ({ documentId, position }: { documentId: number; position: number }) =>
      ApiClient.dueDiligence.reorderDocument(Number(siteId), documentId, position),
    onSuccess: () => {
      previousDocumentsRef.current = documents;
      onRefresh?.();
    },
    onError: (error: any) => {
      notify(error?.response?.data?.detail || 'Failed to reorder document');
      setDocuments(previousDocumentsRef.current);
    }
  });

  const handleDragEnd = (result: DropResult) => {
    if (!result.destination) {
      return;
    }

    if (result.destination.index === result.source.index) {
      return;
    }

    const newDocuments = Array.from(documents);
    const [removed] = newDocuments.splice(result.source.index, 1);
    newDocuments.splice(result.destination.index, 0, removed);

    previousDocumentsRef.current = documents;
    setDocuments(newDocuments);

    reorderMutation.mutate({
      documentId: removed.id,
      position: result.destination.index + 1
    });
  };

  const droppableId = `section-${sectionName.replace(/\s+/g, '-')}`;

  return (
    <DragDropContext onDragEnd={handleDragEnd}>
      <Droppable droppableId={droppableId}>
        {provided => (
          <div ref={provided.innerRef} {...provided.droppableProps}>
            {documents.map((document, index) => (
              <Draggable key={document.id} draggableId={`doc-${document.id}`} index={index}>
                {(provided, snapshot) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.draggableProps}
                    style={{
                      ...provided.draggableProps.style,
                      display: 'flex',
                      alignItems: 'stretch',
                      backgroundColor: snapshot.isDragging ? '#f5f5f5' : 'transparent'
                    }}
                  >
                    <div
                      {...provided.dragHandleProps}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: '32px',
                        cursor: 'grab',
                        backgroundColor: 'rgba(0, 0, 0, 0.02)',
                        borderBottom: '1px solid #E0E0E0'
                      }}
                    >
                      <DragIndicatorIcon sx={{ color: 'text.disabled', fontSize: '20px' }} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <DocumentItem document={document} onRefresh={onRefresh} onDocumentClick={onDocumentClick} />
                    </div>
                  </div>
                )}
              </Draggable>
            ))}
            {provided.placeholder}
          </div>
        )}
      </Droppable>
    </DragDropContext>
  );
};

const RecursiveAccordion: React.FC<RecursiveAccordionProps> = ({
  items,
  forceExpanded,
  onRefresh,
  onDocumentClick
}) => {
  return (
    <>
      {items?.map(item => (
        <ManagedAccordion forceExpanded={forceExpanded} key={item.name}>
          <AccordionSummary
            expandIcon={<ArrowDropDownIcon />}
            aria-controls="panel2-content"
            id="panel2-header"
            sx={theme => ({
              flexDirection: 'row-reverse',
              height: '54px',
              borderBottom: `1px solid ${theme.palette.divider}`,
              backgroundColor: theme.palette.action.hover
            })}
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
            <SortableDocumentList
              documents={item.documents}
              sectionName={item.name}
              onRefresh={onRefresh}
              onDocumentClick={onDocumentClick}
            />
            {!!item?.related_sections.length && (
              <Box sx={{ padding: '16px' }}>
                <RecursiveAccordion
                  forceExpanded={forceExpanded}
                  items={item.related_sections}
                  onRefresh={onRefresh}
                  onDocumentClick={onDocumentClick}
                />
              </Box>
            )}
          </AccordionDetails>
        </ManagedAccordion>
      ))}
    </>
  );
};

export default RecursiveAccordion;

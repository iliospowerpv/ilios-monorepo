import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import Typography from '@mui/material/Typography';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown';
import Box from '@mui/material/Box';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy
} from '@dnd-kit/sortable';

import ProgressBar from '../ProgressBar/ProgressBar';
import SortableDocumentItem from '../DocumentItem/SortableDocumentItem';
import { ApiClient, DiligenceDocument, DiligenceItem } from '../../../../../../../../api';
import { useNotify } from '../../../../../../../../contexts/notifications/notifications';

interface RecursiveAccordionProps {
  items: DiligenceItem[] | undefined;
  forceExpanded?: boolean;
  onRefresh?: () => void;
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

interface SortableDocumentListProps {
  documents: DiligenceDocument[];
  onRefresh?: () => void;
}

const SortableDocumentList: React.FC<SortableDocumentListProps> = ({ documents: initialDocuments, onRefresh }) => {
  const { siteId } = useParams();
  const notify = useNotify();
  const [documents, setDocuments] = useState<DiligenceDocument[]>(initialDocuments);

  React.useEffect(() => {
    setDocuments(initialDocuments);
  }, [initialDocuments]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8
      }
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates
    })
  );

  const previousDocumentsRef = React.useRef<DiligenceDocument[]>(initialDocuments);

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

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = documents.findIndex(doc => doc.id === active.id);
      const newIndex = documents.findIndex(doc => doc.id === over.id);

      previousDocumentsRef.current = documents;
      const newDocuments = arrayMove(documents, oldIndex, newIndex);
      setDocuments(newDocuments);

      const movedDoc = documents[oldIndex];
      reorderMutation.mutate({
        documentId: movedDoc.id,
        position: newIndex + 1
      });
    }
  };

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={documents.map(doc => doc.id)} strategy={verticalListSortingStrategy}>
        {documents.map(document => (
          <SortableDocumentItem key={`doc+${document.id}`} document={document} onRefresh={onRefresh} />
        ))}
      </SortableContext>
    </DndContext>
  );
};

const RecursiveAccordion: React.FC<RecursiveAccordionProps> = ({ items, forceExpanded, onRefresh }) => {
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
            <SortableDocumentList documents={item.documents} onRefresh={onRefresh} />
            {!!item?.related_sections.length && (
              <Box sx={{ padding: '16px' }}>
                <RecursiveAccordion forceExpanded={forceExpanded} items={item.related_sections} onRefresh={onRefresh} />
              </Box>
            )}
          </AccordionDetails>
        </ManagedAccordion>
      ))}
    </>
  );
};

export default RecursiveAccordion;

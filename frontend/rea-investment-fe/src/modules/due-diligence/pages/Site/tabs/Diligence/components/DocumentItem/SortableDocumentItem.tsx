import React from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import Box from '@mui/material/Box';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';

import DocumentItem from './DocumentItem';
import { DiligenceDocument } from '../../../../../../../../api';

interface SortableDocumentItemProps {
  document: DiligenceDocument;
  onRefresh?: () => void;
}

const SortableDocumentItem: React.FC<SortableDocumentItemProps> = ({ document, onRefresh }) => {
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, transition, isDragging } = useSortable({
    id: document.id
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 1000 : 'auto'
  };

  return (
    <Box ref={setNodeRef} style={style} sx={{ display: 'flex', alignItems: 'stretch' }}>
      <Box
        ref={setActivatorNodeRef}
        {...attributes}
        {...listeners}
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '32px',
          cursor: isDragging ? 'grabbing' : 'grab',
          backgroundColor: 'rgba(0, 0, 0, 0.02)',
          borderBottom: '1px solid #E0E0E0',
          touchAction: 'none',
          userSelect: 'none',
          '&:hover': {
            backgroundColor: 'rgba(0, 0, 0, 0.06)'
          }
        }}
      >
        <DragIndicatorIcon sx={{ color: 'rgba(0, 0, 0, 0.4)', fontSize: '20px', pointerEvents: 'none' }} />
      </Box>
      <Box sx={{ flex: 1 }}>
        <DocumentItem document={document} onRefresh={onRefresh} />
      </Box>
    </Box>
  );
};

export default SortableDocumentItem;

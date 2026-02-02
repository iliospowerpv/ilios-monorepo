import React from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  DragStartEvent,
  DragOverlay
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  rectSortingStrategy
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import Box from '@mui/material/Box';
import Collapse from '@mui/material/Collapse';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import Chip from '@mui/material/Chip';
import { useTheme } from '@mui/material/styles';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import Tooltip from '@mui/material/Tooltip';

export interface DealCardItem {
  id: string;
  title: string;
  content: React.ReactNode;
  hasMissingFields?: boolean;
  missingFieldCount?: number;
  missingFieldNames?: string[];
  headerSummary?: string;
}

interface CollapsedState {
  [key: string]: boolean;
}

interface DealDraggableCardLayoutProps {
  cards: DealCardItem[];
  storageKey: string;
  columns?: number;
  defaultOpenCards?: string[];
}

interface SortableCardProps {
  card: DealCardItem;
  isCollapsed: boolean;
  onToggleCollapse: (id: string) => void;
  isDragging?: boolean;
}

const SortableCard: React.FC<SortableCardProps> = ({ card, isCollapsed, onToggleCollapse, isDragging = false }) => {
  const theme = useTheme();
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging: isSortableDragging
  } = useSortable({ id: card.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isSortableDragging ? 0.5 : 1
  };

  const borderColor = card.hasMissingFields ? theme.palette.warning.main : theme.palette.divider;

  return (
    <Box
      ref={setNodeRef}
      style={style}
      sx={{
        border: `1px solid ${borderColor}`,
        borderRadius: 2,
        bgcolor: theme.palette.background.paper,
        overflow: 'hidden',
        boxShadow: isDragging ? 4 : 1
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          p: 1.5,
          bgcolor: theme.palette.mode === 'dark' ? 'grey.900' : 'grey.50',
          borderBottom: isCollapsed ? 'none' : `1px solid ${theme.palette.divider}`,
          cursor: 'pointer'
        }}
        onClick={() => onToggleCollapse(card.id)}
      >
        <Box
          {...attributes}
          {...listeners}
          sx={{ cursor: 'grab', mr: 1, display: 'flex', alignItems: 'center', color: 'text.secondary' }}
          onClick={e => e.stopPropagation()}
        >
          <DragIndicatorIcon fontSize="small" />
        </Box>

        <Stack direction="row" alignItems="center" spacing={1} sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="subtitle2" fontWeight={600} noWrap>
            {card.title}
          </Typography>

          {card.hasMissingFields ? (
            <Tooltip title={`${card.missingFieldCount} missing field${card.missingFieldCount !== 1 ? 's' : ''}`}>
              <Chip
                icon={<WarningAmberIcon sx={{ fontSize: 14 }} />}
                label={card.missingFieldCount}
                size="small"
                color="warning"
                variant="outlined"
                sx={{ height: 20, fontSize: '0.7rem' }}
              />
            </Tooltip>
          ) : (
            <CheckCircleOutlineIcon sx={{ fontSize: 16, color: 'success.main' }} />
          )}
        </Stack>

        {isCollapsed && card.headerSummary && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ mx: 2, flex: '0 1 auto', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
          >
            {card.headerSummary}
          </Typography>
        )}

        <IconButton size="small" onClick={() => onToggleCollapse(card.id)}>
          {isCollapsed ? <ExpandMoreIcon /> : <ExpandLessIcon />}
        </IconButton>
      </Box>

      <Collapse in={!isCollapsed}>
        <Box sx={{ p: 2 }}>{card.content}</Box>
      </Collapse>
    </Box>
  );
};

const CardOverlay: React.FC<{ card: DealCardItem }> = ({ card }) => {
  const theme = useTheme();

  return (
    <Box
      sx={{
        border: `1px solid ${theme.palette.primary.main}`,
        borderRadius: 2,
        bgcolor: theme.palette.background.paper,
        boxShadow: 6,
        p: 1.5,
        transform: 'rotate(3deg)'
      }}
    >
      <Stack direction="row" alignItems="center" spacing={1}>
        <DragIndicatorIcon fontSize="small" sx={{ color: 'text.secondary' }} />
        <Typography variant="subtitle2" fontWeight={600}>
          {card.title}
        </Typography>
      </Stack>
    </Box>
  );
};

export const DealDraggableCardLayout: React.FC<DealDraggableCardLayoutProps> = ({
  cards,
  storageKey,
  columns = 2,
  defaultOpenCards = []
}) => {
  const [cardOrder, setCardOrder] = React.useState<string[]>(() => {
    try {
      const saved = localStorage.getItem(`${storageKey}_order`);
      if (saved) {
        const parsed = JSON.parse(saved);
        const cardIds = cards.map(c => c.id);
        const validOrder = parsed.filter((id: string) => cardIds.includes(id));
        const newCards = cardIds.filter(id => !validOrder.includes(id));
        return [...validOrder, ...newCards];
      }
    } catch {
      // Ignore localStorage errors
    }
    return cards.map(c => c.id);
  });

  const [collapsedState, setCollapsedState] = React.useState<CollapsedState>(() => {
    try {
      const saved = localStorage.getItem(`${storageKey}_collapsed`);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch {
      // Ignore localStorage errors
    }
    const initial: CollapsedState = {};
    cards.forEach((card, index) => {
      initial[card.id] = !defaultOpenCards.includes(card.id) && index >= 2;
    });
    return initial;
  });

  const [activeId, setActiveId] = React.useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  React.useEffect(() => {
    localStorage.setItem(`${storageKey}_order`, JSON.stringify(cardOrder));
  }, [cardOrder, storageKey]);

  React.useEffect(() => {
    localStorage.setItem(`${storageKey}_collapsed`, JSON.stringify(collapsedState));
  }, [collapsedState, storageKey]);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (over && active.id !== over.id) {
      setCardOrder(prev => {
        const oldIndex = prev.indexOf(active.id as string);
        const newIndex = prev.indexOf(over.id as string);
        return arrayMove(prev, oldIndex, newIndex);
      });
    }
  };

  const handleToggleCollapse = (id: string) => {
    setCollapsedState(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const orderedCards = cardOrder
    .map(id => cards.find(c => c.id === id))
    .filter((c): c is DealCardItem => c !== undefined);

  const activeCard = activeId ? cards.find(c => c.id === activeId) : null;

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <SortableContext items={cardOrder} strategy={rectSortingStrategy}>
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', md: `repeat(${columns}, 1fr)` },
            gap: 2
          }}
        >
          {orderedCards.map(card => (
            <SortableCard
              key={card.id}
              card={card}
              isCollapsed={collapsedState[card.id] ?? false}
              onToggleCollapse={handleToggleCollapse}
              isDragging={activeId === card.id}
            />
          ))}
        </Box>
      </SortableContext>

      <DragOverlay>{activeCard ? <CardOverlay card={activeCard} /> : null}</DragOverlay>
    </DndContext>
  );
};

export default DealDraggableCardLayout;

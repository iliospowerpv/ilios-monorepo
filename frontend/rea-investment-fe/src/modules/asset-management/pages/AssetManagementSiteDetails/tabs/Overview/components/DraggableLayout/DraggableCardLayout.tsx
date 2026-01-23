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
import { useTheme } from '@mui/material/styles';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';

export interface CardItem {
  id: string;
  title: string;
  content: React.ReactNode;
}

interface CollapsedState {
  [key: string]: boolean;
}

interface DraggableCardLayoutProps {
  cards: CardItem[];
  storageKey: string;
  columns?: number;
}

interface SortableCardProps {
  card: CardItem;
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
    isDragging: isSorting
  } = useSortable({
    id: card.id
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isSorting ? 0.5 : 1
  };

  const borderColor = theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.12)';
  const hoverBgColor = theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.04)' : 'rgba(0, 0, 0, 0.02)';

  return (
    <Box
      ref={setNodeRef}
      style={style}
      sx={{
        mb: 1,
        border: `1px solid ${borderColor}`,
        borderRadius: '8px',
        backgroundColor: theme.palette.background.paper,
        boxShadow: isDragging ? theme.shadows[4] : 'none',
        '&:hover': {
          backgroundColor: hoverBgColor
        }
      }}
    >
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{
          p: 1,
          cursor: 'pointer',
          borderBottom: isCollapsed ? 'none' : `1px solid ${borderColor}`
        }}
      >
        <Stack direction="row" alignItems="center" spacing={1}>
          <Box
            {...attributes}
            {...listeners}
            sx={{
              cursor: 'grab',
              display: 'flex',
              alignItems: 'center',
              color: theme.palette.text.secondary,
              '&:hover': {
                color: theme.palette.primary.main
              }
            }}
          >
            <DragIndicatorIcon fontSize="small" />
          </Box>
          <Typography
            variant="subtitle1"
            fontWeight={600}
            onClick={() => onToggleCollapse(card.id)}
            sx={{ cursor: 'pointer', userSelect: 'none' }}
          >
            {card.title}
          </Typography>
        </Stack>
        <IconButton size="small" onClick={() => onToggleCollapse(card.id)}>
          {isCollapsed ? <ExpandMoreIcon fontSize="small" /> : <ExpandLessIcon fontSize="small" />}
        </IconButton>
      </Stack>
      <Collapse in={!isCollapsed}>
        <Box>{card.content}</Box>
      </Collapse>
    </Box>
  );
};

const DraggableCardLayout: React.FC<DraggableCardLayoutProps> = ({ cards, storageKey, columns = 3 }) => {
  const theme = useTheme();
  const [activeId, setActiveId] = React.useState<string | null>(null);

  const getStoredOrder = React.useCallback((): string[] => {
    try {
      const stored = localStorage.getItem(`${storageKey}_order`);
      if (stored) {
        const parsed = JSON.parse(stored);
        const validIds = cards.map(c => c.id);
        const filteredOrder = parsed.filter((id: string) => validIds.includes(id));
        const missingIds = validIds.filter(id => !filteredOrder.includes(id));
        return [...filteredOrder, ...missingIds];
      }
    } catch (e) {
      console.error('Error loading card order from localStorage:', e);
    }
    return cards.map(c => c.id);
  }, [cards, storageKey]);

  const getStoredCollapsedState = React.useCallback((): CollapsedState => {
    try {
      const stored = localStorage.getItem(`${storageKey}_collapsed`);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (e) {
      console.error('Error loading collapsed state from localStorage:', e);
    }
    return {};
  }, [storageKey]);

  const [cardOrder, setCardOrder] = React.useState<string[]>(getStoredOrder);
  const [collapsedState, setCollapsedState] = React.useState<CollapsedState>(getStoredCollapsedState);

  React.useEffect(() => {
    setCardOrder(getStoredOrder());
    setCollapsedState(getStoredCollapsedState());
  }, [storageKey, getStoredOrder, getStoredCollapsedState]);

  React.useEffect(() => {
    localStorage.setItem(`${storageKey}_order`, JSON.stringify(cardOrder));
  }, [cardOrder, storageKey]);

  React.useEffect(() => {
    localStorage.setItem(`${storageKey}_collapsed`, JSON.stringify(collapsedState));
  }, [collapsedState, storageKey]);

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

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (over && active.id !== over.id) {
      setCardOrder(items => {
        const oldIndex = items.indexOf(active.id as string);
        const newIndex = items.indexOf(over.id as string);
        return arrayMove(items, oldIndex, newIndex);
      });
    }
  };

  const handleToggleCollapse = (id: string) => {
    setCollapsedState(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const orderedCards = React.useMemo(() => {
    const cardMap = new Map(cards.map(c => [c.id, c]));
    return cardOrder.map(id => cardMap.get(id)).filter((card): card is CardItem => card !== undefined);
  }, [cards, cardOrder]);

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
            gridTemplateColumns: {
              xs: '1fr',
              md: `repeat(${Math.min(columns, 2)}, 1fr)`,
              lg: `repeat(${columns}, 1fr)`
            },
            gap: 1,
            mb: '12px'
          }}
        >
          {orderedCards.map(card => (
            <SortableCard
              key={card.id}
              card={card}
              isCollapsed={!!collapsedState[card.id]}
              onToggleCollapse={handleToggleCollapse}
            />
          ))}
        </Box>
      </SortableContext>
      <DragOverlay>
        {activeCard ? (
          <Box
            sx={{
              border: `1px solid ${theme.palette.divider}`,
              borderRadius: '8px',
              backgroundColor: theme.palette.background.paper,
              boxShadow: theme.shadows[8],
              p: 1
            }}
          >
            <Stack direction="row" alignItems="center" spacing={1}>
              <DragIndicatorIcon fontSize="small" color="primary" />
              <Typography variant="subtitle1" fontWeight={600}>
                {activeCard.title}
              </Typography>
            </Stack>
          </Box>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
};

export default DraggableCardLayout;

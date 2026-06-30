import * as React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardActions from '@mui/material/CardActions';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import LaunchIcon from '@mui/icons-material/Launch';
import QuestionAnswerOutlinedIcon from '@mui/icons-material/QuestionAnswerOutlined';

import type { AssistantActionCard } from '../../api/assistant';

const KIND_LABEL: Record<AssistantActionCard['kind'], string> = {
  workflow: 'Start workflow',
  sequence: 'Start sequence',
  resume: 'Resume run',
  open: 'Open view',
  explain: 'Explain'
};

interface ActionCardItemProps {
  card: AssistantActionCard;
  // Navigate the USER to the deep link. The assistant never executes — clicking is the human action.
  onOpen: (route: string) => void;
  // Re-submit an `explain` card's prompt into the read-only chat (no navigation). Required for
  // `explain` cards; ignored for every other kind.
  onPrompt?: (prompt: string) => void;
  // Bounded UI-interaction analytics for a card click (records the card kind only, never its target).
  onTrackClick?: (card: AssistantActionCard) => void;
  disabled?: boolean;
}

export const ActionCardItem: React.FC<ActionCardItemProps> = ({ card, onOpen, onPrompt, onTrackClick, disabled }) => {
  // `explain` re-prompts the read-only chat in place; every other kind is an inert deep link the user
  // clicks to navigate. Both remain propose-only — the assistant never acts on the user's behalf.
  const isExplain = card.kind === 'explain';
  const canExplain = isExplain && Boolean(card.prompt);
  const handleClick = () => {
    onTrackClick?.(card);
    if (isExplain) {
      if (card.prompt) onPrompt?.(card.prompt);
    } else {
      onOpen(card.route);
    }
  };

  return (
    <Card variant="outlined" sx={{ borderColor: 'secondary.main', bgcolor: 'background.paper' }}>
      <CardContent sx={{ pb: 1 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
          <Chip label={KIND_LABEL[card.kind]} size="small" color="secondary" variant="outlined" />
        </Stack>
        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
          {card.title}
        </Typography>
        {card.reason ? (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {card.reason}
          </Typography>
        ) : null}
      </CardContent>
      <CardActions sx={{ px: 2, pb: 1.5, pt: 0 }}>
        <Button
          size="small"
          variant="contained"
          color="secondary"
          endIcon={isExplain ? <QuestionAnswerOutlinedIcon /> : <LaunchIcon />}
          onClick={handleClick}
          disabled={disabled || (isExplain && !canExplain)}
        >
          {isExplain ? 'Ask' : 'Open'}
        </Button>
        <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
          {isExplain ? 'The assistant explains — read-only.' : 'You take this step — the assistant can\u2019t.'}
        </Typography>
      </CardActions>
    </Card>
  );
};

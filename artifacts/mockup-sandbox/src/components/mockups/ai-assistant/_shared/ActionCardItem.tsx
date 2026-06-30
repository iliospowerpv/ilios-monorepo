import * as React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardActions from '@mui/material/CardActions';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import LaunchIcon from '@mui/icons-material/Launch';

import type { AssistantActionCard } from './assistant-types';

const KIND_LABEL: Record<AssistantActionCard['kind'], string> = {
  workflow: 'Start workflow',
  sequence: 'Start sequence',
  resume: 'Resume run'
};

interface ActionCardItemProps {
  card: AssistantActionCard;
  // Navigate the USER to the deep link. The assistant never executes — clicking is the human action.
  onOpen: (route: string) => void;
}

export const ActionCardItem: React.FC<ActionCardItemProps> = ({ card, onOpen }) => {
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
          endIcon={<LaunchIcon />}
          onClick={() => onOpen(card.route)}
        >
          Open
        </Button>
        <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
          You take this step — the assistant can&apos;t.
        </Typography>
      </CardActions>
    </Card>
  );
};

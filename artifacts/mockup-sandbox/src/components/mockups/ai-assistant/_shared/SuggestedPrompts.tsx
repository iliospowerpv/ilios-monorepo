import * as React from 'react';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';

import type { AssistantSuggestedPrompt } from './assistant-types';

interface SuggestedPromptsProps {
  prompts: AssistantSuggestedPrompt[];
  contextLabel?: string | null;
  disabled?: boolean;
  onPick: (prompt: string) => void;
}

// Pure UI affordance shown in the empty chat state. The chips are static, page-aware examples — no
// business data is fetched to build them and picking one simply sends that text as a normal turn.
export const SuggestedPrompts: React.FC<SuggestedPromptsProps> = ({ prompts, contextLabel, disabled, onPick }) => {
  if (!prompts || prompts.length === 0) {
    return null;
  }

  return (
    <Box sx={{ mt: 2 }}>
      <Typography variant="caption" color="text.secondary">
        {contextLabel ? `Try asking — ${contextLabel}` : 'Try asking'}
      </Typography>
      <Stack direction="row" sx={{ mt: 1, flexWrap: 'wrap', gap: 0.5 }}>
        {prompts.map((prompt, idx) => (
          <Chip
            key={`${idx}-${prompt.label}`}
            label={prompt.label}
            size="small"
            variant="outlined"
            color="secondary"
            clickable
            disabled={disabled}
            onClick={() => onPick(prompt.prompt)}
          />
        ))}
      </Stack>
    </Box>
  );
};

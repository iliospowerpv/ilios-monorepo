import * as React from 'react';
import Stack from '@mui/material/Stack';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import ThumbUpOutlinedIcon from '@mui/icons-material/ThumbUpOutlined';
import ThumbUpAltIcon from '@mui/icons-material/ThumbUpAlt';
import ThumbDownOutlinedIcon from '@mui/icons-material/ThumbDownOutlined';
import ThumbDownAltIcon from '@mui/icons-material/ThumbDownAlt';

import type { AssistantFeedbackRating } from './assistant-types';

interface MessageFeedbackProps {
  value?: AssistantFeedbackRating | null;
  disabled?: boolean;
  onChange: (rating: AssistantFeedbackRating | null) => void;
}

// Owner-scoped thumbs on a persisted assistant reply. Clicking the active rating clears it (sends
// `null`). This records reaction only — it never triggers a governed/business action.
export const MessageFeedback: React.FC<MessageFeedbackProps> = ({ value, disabled, onChange }) => {
  const toggle = (rating: AssistantFeedbackRating) => onChange(value === rating ? null : rating);

  return (
    <Stack direction="row" alignItems="center">
      <Tooltip title="Helpful">
        <span>
          <IconButton
            size="small"
            disabled={disabled}
            aria-label="Mark reply helpful"
            aria-pressed={value === 'up'}
            onClick={() => toggle('up')}
          >
            {value === 'up' ? (
              <ThumbUpAltIcon sx={{ fontSize: 15 }} color="secondary" />
            ) : (
              <ThumbUpOutlinedIcon sx={{ fontSize: 15 }} />
            )}
          </IconButton>
        </span>
      </Tooltip>
      <Tooltip title="Not helpful">
        <span>
          <IconButton
            size="small"
            disabled={disabled}
            aria-label="Mark reply not helpful"
            aria-pressed={value === 'down'}
            onClick={() => toggle('down')}
          >
            {value === 'down' ? (
              <ThumbDownAltIcon sx={{ fontSize: 15 }} color="error" />
            ) : (
              <ThumbDownOutlinedIcon sx={{ fontSize: 15 }} />
            )}
          </IconButton>
        </span>
      </Tooltip>
    </Stack>
  );
};

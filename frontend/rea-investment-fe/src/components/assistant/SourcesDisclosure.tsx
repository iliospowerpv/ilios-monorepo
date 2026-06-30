import * as React from 'react';
import Box from '@mui/material/Box';
import Link from '@mui/material/Link';
import Collapse from '@mui/material/Collapse';
import Stack from '@mui/material/Stack';
import Chip from '@mui/material/Chip';
import Tooltip from '@mui/material/Tooltip';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import MenuBookOutlinedIcon from '@mui/icons-material/MenuBookOutlined';
import StorageOutlinedIcon from '@mui/icons-material/StorageOutlined';

import type { AssistantSource } from '../../api/assistant';

interface SourcesDisclosureProps {
  sources: AssistantSource[];
  // Fired only when the user EXPANDS the disclosure (transparency engagement). Bounded analytics —
  // no source labels/refs are reported, just the fact that it was opened.
  onOpen?: () => void;
}

// Transparency-only affordance: a collapsible list of the curated FAQ entries and read-only data
// tools that backed a reply. It never renders raw tool payloads — only stable labels/identifiers.
export const SourcesDisclosure: React.FC<SourcesDisclosureProps> = ({ sources, onOpen }) => {
  const [open, setOpen] = React.useState(false);

  if (!sources || sources.length === 0) {
    return null;
  }

  const handleToggle = () =>
    setOpen(value => {
      const next = !value;
      if (next) onOpen?.();
      return next;
    });

  return (
    <Box sx={{ width: '85%' }}>
      <Link
        component="button"
        type="button"
        variant="caption"
        underline="hover"
        color="text.secondary"
        onClick={handleToggle}
        sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.25 }}
      >
        {open ? <ExpandLessIcon sx={{ fontSize: 14 }} /> : <ExpandMoreIcon sx={{ fontSize: 14 }} />}
        Sources ({sources.length})
      </Link>
      <Collapse in={open} unmountOnExit>
        <Stack direction="row" sx={{ mt: 0.5, flexWrap: 'wrap', gap: 0.5 }}>
          {sources.map((source, idx) => {
            const isFaq = source.kind === 'faq';
            const chip = (
              <Chip
                size="small"
                variant="outlined"
                icon={isFaq ? <MenuBookOutlinedIcon /> : <StorageOutlinedIcon />}
                label={source.label}
              />
            );
            const key = `${source.kind}-${source.ref ?? idx}`;
            return source.detail ? (
              <Tooltip key={key} title={source.detail}>
                {chip}
              </Tooltip>
            ) : (
              <Box component="span" key={key}>
                {chip}
              </Box>
            );
          })}
        </Stack>
      </Collapse>
    </Box>
  );
};

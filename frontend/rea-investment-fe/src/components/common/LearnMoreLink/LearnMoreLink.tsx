import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Typography from '@mui/material/Typography';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import Link from '@mui/material/Link';
import Stack from '@mui/material/Stack';

interface LearnMoreLinkProps {
  articleSlug: string;
  label?: string;
}

export const LearnMoreLink: React.FC<LearnMoreLinkProps> = ({ articleSlug, label = 'Learn more' }) => {
  return (
    <Link
      component={RouterLink}
      to={`/help?article=${articleSlug}`}
      underline="none"
      onClick={e => e.stopPropagation()}
      sx={{
        display: 'inline-flex',
        borderRadius: 1,
        px: 0.5,
        py: 0.25,
        '&:hover .learn-more-text': { textDecoration: 'underline' }
      }}
    >
      <Stack direction="row" alignItems="center" spacing={0.5}>
        <HelpOutlineIcon sx={{ fontSize: 16, color: 'primary.main' }} />
        <Typography className="learn-more-text" variant="caption" color="primary.main" sx={{ fontWeight: 500 }}>
          {label}
        </Typography>
      </Stack>
    </Link>
  );
};

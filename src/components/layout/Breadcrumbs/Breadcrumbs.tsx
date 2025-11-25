import React from 'react';
import { useMatches, Link as RouterLink } from 'react-router-dom';
import MuiBreadcrumbs from '@mui/material/Breadcrumbs';
import Link from '@mui/material/Link';
import { RouteHandle } from '../../../handles';

export const Breadcrumbs: React.FC = () => {
  const matches = useMatches();
  const crumbList = matches
    .map(({ handle, data }) => (handle instanceof RouteHandle ? handle.buildCrumbs(data) : []))
    .flat();

  return (
    <MuiBreadcrumbs
      sx={{ flexGrow: 1, color: 'text.secondary', fontWeight: '400', fontSize: '14px', lineHeight: '1.4' }}
    >
      {crumbList.map(({ title, link }) =>
        link ? (
          <Link component={RouterLink} to={link} key={title} underline="hover" color="inherit">
            {title}
          </Link>
        ) : (
          <Link key={title} underline="none" color="text.primary">
            {title}
          </Link>
        )
      )}
    </MuiBreadcrumbs>
  );
};

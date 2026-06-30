import React from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Button from '@mui/material/Button';
import BusinessIcon from '@mui/icons-material/Business';
import FolderIcon from '@mui/icons-material/Folder';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import Skeleton from '@mui/material/Skeleton';

import type { WorkspaceCompany } from '../../../../api/workspace';

interface HomeCompaniesProps {
  companies: WorkspaceCompany[];
  isLoading?: boolean;
}

const getRoleColor = (role: string | null): 'primary' | 'secondary' | 'default' => {
  if (!role) return 'default';
  switch (role) {
    case 'company_admin':
      return 'primary';
    case 'contributor':
      return 'secondary';
    default:
      return 'default';
  }
};

const getRoleLabel = (role: string | null): string => {
  if (!role) return 'Project Access';
  switch (role) {
    case 'company_admin':
      return 'Admin';
    case 'contributor':
      return 'Contributor';
    case 'read_only':
      return 'Read Only';
    default:
      return role;
  }
};

const getAccessSourceLabel = (source: string): string => {
  switch (source) {
    case 'membership':
      return 'Direct Member';
    case 'project':
      return 'Via Project';
    case 'legacy':
      return 'Legacy Access';
    default:
      return source;
  }
};

export const HomeCompanies: React.FC<HomeCompaniesProps> = ({ companies, isLoading }) => {
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <Box sx={{ height: '100%', minHeight: 0, overflow: 'auto', p: 2 }}>
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
            gap: 2
          }}
        >
          {[1, 2, 3].map(i => (
            <Skeleton key={i} variant="rectangular" height={120} sx={{ borderRadius: 1 }} />
          ))}
        </Box>
      </Box>
    );
  }

  if (companies.length === 0) {
    return (
      <Box
        sx={{
          height: '100%',
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          p: 2
        }}
      >
        <BusinessIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
        <Typography color="text.secondary">You don&apos;t have access to any companies yet.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', minHeight: 0, overflow: 'auto', p: 2 }}>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
          gap: 2
        }}
      >
        {companies.map(company => (
          <Card
            key={company.company_id}
            variant="outlined"
            sx={{
              height: '100%',
              '&:hover': {
                borderColor: 'primary.main',
                boxShadow: 1
              }
            }}
          >
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 1, mb: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
                  <BusinessIcon color="primary" />
                  <Typography variant="subtitle1" fontWeight={500} noWrap>
                    {company.company_name}
                  </Typography>
                </Box>
                <Chip
                  size="small"
                  label={getRoleLabel(company.role)}
                  color={getRoleColor(company.role)}
                  variant="outlined"
                  sx={{ flexShrink: 0 }}
                />
              </Box>

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2, flexWrap: 'wrap' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <FolderIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                  <Typography variant="body2" color="text.secondary">
                    {company.project_count} project{company.project_count !== 1 ? 's' : ''}
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.disabled">
                  {getAccessSourceLabel(company.access_source)}
                </Typography>
              </Box>

              <Button
                variant="outlined"
                size="small"
                endIcon={<OpenInNewIcon />}
                onClick={() => navigate(`/project-hub/companies/${company.company_id}`)}
                fullWidth
              >
                Open Company
              </Button>
            </CardContent>
          </Card>
        ))}
      </Box>
    </Box>
  );
};

export default HomeCompanies;

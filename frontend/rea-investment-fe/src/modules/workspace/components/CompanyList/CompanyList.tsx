import React from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Chip from '@mui/material/Chip';
import BusinessIcon from '@mui/icons-material/Business';
import FolderIcon from '@mui/icons-material/Folder';
import Skeleton from '@mui/material/Skeleton';

import type { WorkspaceCompany } from '../../../../api/workspace';

interface CompanyListProps {
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

export const CompanyList: React.FC<CompanyListProps> = ({ companies, isLoading }) => {
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Your Companies
          </Typography>
          <List>
            {[1, 2, 3].map(i => (
              <Box key={i} sx={{ py: 1.5 }}>
                <Skeleton variant="rectangular" height={60} sx={{ borderRadius: 1 }} />
              </Box>
            ))}
          </List>
        </CardContent>
      </Card>
    );
  }

  if (companies.length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Your Companies
          </Typography>
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <BusinessIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
            <Typography color="text.secondary">You don&apos;t have access to any companies yet.</Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Your Companies
        </Typography>
        <List disablePadding>
          {companies.map(company => (
            <ListItemButton
              key={company.company_id}
              onClick={() => navigate(`/project-hub/companies/${company.company_id}`)}
              sx={{
                borderRadius: 1,
                mb: 1,
                border: '1px solid',
                borderColor: 'divider',
                '&:hover': {
                  backgroundColor: 'action.hover'
                }
              }}
            >
              <ListItemIcon>
                <BusinessIcon color="primary" />
              </ListItemIcon>
              <ListItemText
                primary={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="subtitle1" fontWeight={500}>
                      {company.company_name}
                    </Typography>
                    <Chip
                      size="small"
                      label={getRoleLabel(company.role)}
                      color={getRoleColor(company.role)}
                      variant="outlined"
                    />
                  </Box>
                }
                secondary={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 0.5 }}>
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
                }
              />
            </ListItemButton>
          ))}
        </List>
      </CardContent>
    </Card>
  );
};

export default CompanyList;

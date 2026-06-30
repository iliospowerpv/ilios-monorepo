import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Button from '@mui/material/Button';
import FolderIcon from '@mui/icons-material/Folder';
import BusinessIcon from '@mui/icons-material/Business';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import Skeleton from '@mui/material/Skeleton';

import type { WorkspaceProject } from '../../../../api/workspace';
import { ApiClient } from '../../../../api';
import type { InventoryReconciliationSummary } from '../../../../types/telemetryV2';
import InventoryReconciliationChip from '../../../../components/common/InventoryReconciliationChip/InventoryReconciliationChip';

interface HomeProjectsProps {
  projects: WorkspaceProject[];
  isLoading?: boolean;
}

export const HomeProjects: React.FC<HomeProjectsProps> = ({ projects, isLoading }) => {
  const navigate = useNavigate();

  // One reconciliation-summary request for the whole card set (not one per card).
  const sortedSiteIds = useMemo(
    () =>
      projects
        .map(p => p.project_id)
        .filter((id): id is number => typeof id === 'number')
        .sort((a, b) => a - b),
    [projects]
  );
  const {
    data: reconData,
    isFetching: reconFetching,
    isError: reconIsError
  } = useQuery({
    queryKey: ['inventory-reconciliation-summaries', sortedSiteIds],
    queryFn: () => ApiClient.telemetryV2.getInventoryReconciliationSummaries(sortedSiteIds),
    enabled: sortedSiteIds.length > 0,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
    retry: 1
  });
  const reconMap = useMemo(() => {
    const map = new Map<number, InventoryReconciliationSummary>();
    (reconData?.summaries ?? []).forEach(item => map.set(item.site_id, item.summary));
    return map;
  }, [reconData]);

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
            <Skeleton key={i} variant="rectangular" height={140} sx={{ borderRadius: 1 }} />
          ))}
        </Box>
      </Box>
    );
  }

  if (projects.length === 0) {
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
        <FolderIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
        <Typography color="text.secondary">You don&apos;t have access to any projects yet.</Typography>
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
        {projects.map(project => {
          const location = [project.city, project.state].filter(Boolean).join(', ');

          return (
            <Card
              key={project.project_id}
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
                <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
                    <FolderIcon color="primary" />
                    <Typography variant="subtitle1" fontWeight={500} noWrap>
                      {project.project_name}
                    </Typography>
                  </Box>
                </Box>

                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1, flexWrap: 'wrap' }}>
                  <BusinessIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                  <Chip size="small" label={project.company_name} variant="outlined" />
                </Box>

                <Box sx={{ mb: 1 }}>
                  <InventoryReconciliationChip
                    summary={reconMap.get(project.project_id)}
                    loading={reconFetching && !reconMap.get(project.project_id)}
                    error={reconIsError && !reconMap.get(project.project_id)}
                    to={`/project-hub/projects/${project.project_id}/reconciliation`}
                  />
                </Box>

                {location && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                    <LocationOnIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                    <Typography variant="body2" color="text.secondary">
                      {location}
                    </Typography>
                  </Box>
                )}

                {(project.system_size_ac || project.system_size_dc) && (
                  <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mb: 1 }}>
                    {project.system_size_ac ? `${project.system_size_ac} kW AC` : ''}
                    {project.system_size_ac && project.system_size_dc ? ' / ' : ''}
                    {project.system_size_dc ? `${project.system_size_dc} kW DC` : ''}
                  </Typography>
                )}

                <Button
                  variant="outlined"
                  size="small"
                  endIcon={<OpenInNewIcon />}
                  onClick={() => navigate(`/project-hub/projects/${project.project_id}`)}
                  fullWidth
                >
                  Open Project
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </Box>
    </Box>
  );
};

export default HomeProjects;

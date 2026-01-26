import React, { useState, useCallback, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  ToggleButtonGroup,
  ToggleButton,
  Tooltip,
  Paper,
  Stack,
  Avatar,
  LinearProgress
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import ViewKanbanIcon from '@mui/icons-material/ViewKanban';
import ViewListIcon from '@mui/icons-material/ViewList';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import { useQuery } from '@tanstack/react-query';

import { useEntityContext } from '../../../../contexts/entityContext';
import { salesApi } from '../../api/sales';
import { SalesPipelineSummary, SalesStage, SALES_STAGE_LABELS, SALES_STAGE_COLORS } from '../../types';

type ViewMode = 'kanban' | 'list';

const STAGE_ORDER: SalesStage[] = [
  SalesStage.Discovery,
  SalesStage.Qualified,
  SalesStage.LOITermSheet,
  SalesStage.UnderContract,
  SalesStage.HandoffToDiligence
];

const formatCurrency = (value?: number): string => {
  if (value === undefined || value === null) return '-';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
};

const formatDate = (dateString?: string): string => {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric'
  });
};

interface ProjectCardProps {
  project: SalesPipelineSummary;
  onClick: () => void;
}

const ProjectCard: React.FC<ProjectCardProps> = ({ project, onClick }) => {
  const isOverdue = project.next_action_date && new Date(project.next_action_date) < new Date();

  return (
    <Card
      sx={{
        mb: 1,
        cursor: 'pointer',
        transition: 'box-shadow 0.2s',
        '&:hover': { boxShadow: 3 }
      }}
      onClick={onClick}
    >
      <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
        <Typography variant="subtitle2" fontWeight={600} noWrap>
          {project.name}
        </Typography>
        <Typography variant="caption" color="text.secondary" noWrap>
          {project.company_name}
        </Typography>

        <Box sx={{ mt: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="body2" fontWeight={500}>
            {formatCurrency(project.pipeline_value)}
          </Typography>
          {project.probability !== undefined && (
            <Chip label={`${project.probability}%`} size="small" sx={{ height: 20, fontSize: '0.7rem' }} />
          )}
        </Box>

        <Box sx={{ mt: 1, display: 'flex', gap: 1, alignItems: 'center' }}>
          {project.assigned_owner && (
            <Tooltip title={`${project.assigned_owner.first_name} ${project.assigned_owner.last_name}`}>
              <Avatar sx={{ width: 20, height: 20, fontSize: '0.7rem' }}>{project.assigned_owner.first_name[0]}</Avatar>
            </Tooltip>
          )}
          {project.next_action_date && (
            <Chip
              icon={<CalendarTodayIcon sx={{ fontSize: 12 }} />}
              label={formatDate(project.next_action_date)}
              size="small"
              color={isOverdue ? 'error' : 'default'}
              sx={{ height: 20, fontSize: '0.65rem' }}
            />
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

interface KanbanColumnProps {
  stage: SalesStage;
  projects: SalesPipelineSummary[];
  onProjectClick: (projectId: number) => void;
}

const KanbanColumn: React.FC<KanbanColumnProps> = ({ stage, projects, onProjectClick }) => {
  const totalValue = projects.reduce((sum, p) => sum + (p.pipeline_value || 0), 0);

  return (
    <Paper
      sx={{
        flex: '1 1 0',
        minWidth: 220,
        maxWidth: 280,
        bgcolor: 'grey.50',
        p: 1.5,
        display: 'flex',
        flexDirection: 'column'
      }}
      elevation={0}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          mb: 1.5,
          pb: 1,
          borderBottom: 3,
          borderColor: SALES_STAGE_COLORS[stage]
        }}
      >
        <Typography variant="subtitle2" fontWeight={600} sx={{ flex: 1 }}>
          {SALES_STAGE_LABELS[stage]}
        </Typography>
        <Chip label={projects.length} size="small" sx={{ height: 20 }} />
      </Box>

      <Typography variant="caption" color="text.secondary" sx={{ mb: 1 }}>
        {formatCurrency(totalValue)} total
      </Typography>

      <Box sx={{ flex: 1, overflowY: 'auto', maxHeight: 'calc(100vh - 280px)' }}>
        {projects.map(project => (
          <ProjectCard key={project.id} project={project} onClick={() => onProjectClick(project.id)} />
        ))}
        {projects.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 3 }}>
            No projects
          </Typography>
        )}
      </Box>
    </Paper>
  );
};

export const SalesHome: React.FC = () => {
  const navigate = useNavigate();
  const { currentCompany, setCurrentProject, setCurrentModule } = useEntityContext();
  const [viewMode, setViewMode] = useState<ViewMode>('kanban');

  useEffect(() => {
    setCurrentModule('sales');
    setCurrentProject(null);
  }, [setCurrentModule, setCurrentProject]);

  const { data: pipeline, isLoading } = useQuery({
    queryKey: ['sales-pipeline', currentCompany?.id],
    queryFn: () => salesApi.getPipeline(currentCompany?.id)
  });

  const handleProjectClick = useCallback(
    (projectId: number) => {
      navigate(`/sales/project/${projectId}`);
    },
    [navigate]
  );

  const totalProjects = pipeline ? Object.values(pipeline).reduce((sum, stage) => sum + stage.length, 0) : 0;

  const totalValue = pipeline
    ? Object.values(pipeline)
        .flat()
        .reduce((sum, p) => sum + (p.pipeline_value || 0), 0)
    : 0;

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box
        sx={{
          px: 3,
          py: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: 1,
          borderColor: 'divider'
        }}
      >
        <Typography variant="h5" fontWeight={600}>
          Sales Pipeline
        </Typography>
        <ToggleButtonGroup value={viewMode} exclusive onChange={(_, v) => v && setViewMode(v)} size="small">
          <ToggleButton value="kanban">
            <ViewKanbanIcon fontSize="small" />
          </ToggleButton>
          <ToggleButton value="list">
            <ViewListIcon fontSize="small" />
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      <Box sx={{ px: 3, py: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Stack direction="row" spacing={3}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Total Projects
            </Typography>
            <Typography variant="h6">{totalProjects}</Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Total Pipeline Value
            </Typography>
            <Typography variant="h6">{formatCurrency(totalValue)}</Typography>
          </Box>
        </Stack>
      </Box>

      {isLoading && <LinearProgress />}

      {!isLoading && pipeline && (
        <Box sx={{ flex: 1, p: 2, overflow: 'auto' }}>
          {viewMode === 'kanban' ? (
            <Box sx={{ display: 'flex', gap: 2, height: '100%' }}>
              {STAGE_ORDER.map(stage => (
                <KanbanColumn
                  key={stage}
                  stage={stage}
                  projects={pipeline[stage.replace('-', '_') as keyof typeof pipeline] || []}
                  onProjectClick={handleProjectClick}
                />
              ))}
            </Box>
          ) : (
            <Paper sx={{ p: 2 }}>
              <Typography variant="body2" color="text.secondary">
                List view coming soon...
              </Typography>
            </Paper>
          )}
        </Box>
      )}
    </Box>
  );
};

export default SalesHome;

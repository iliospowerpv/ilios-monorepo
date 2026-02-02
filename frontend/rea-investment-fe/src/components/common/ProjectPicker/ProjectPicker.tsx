import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import ListItemIcon from '@mui/material/ListItemIcon';
import TextField from '@mui/material/TextField';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';
import SolarPowerIcon from '@mui/icons-material/SolarPower';
import BusinessIcon from '@mui/icons-material/Business';
import InputAdornment from '@mui/material/InputAdornment';
import SearchIcon from '@mui/icons-material/Search';
import { ApiClient } from '../../../api';

export interface ProjectInfo {
  id: number;
  name: string;
  companyId?: number;
  companyName?: string;
}

interface ProjectPickerProps {
  open: boolean;
  onClose: () => void;
  onSelect: (project: ProjectInfo) => void;
  title?: string;
}

export const ProjectPicker: React.FC<ProjectPickerProps> = ({
  open,
  onClose,
  onSelect,
  title = 'Select a Project'
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  const { data: accessibleEntities, isLoading } = useQuery({
    queryKey: ['accessible-entities-picker'],
    queryFn: () => ApiClient.accessibleEntities.getAccessibleEntities(),
    enabled: open,
    staleTime: 5 * 60 * 1000
  });

  const projects = useMemo(() => {
    if (!accessibleEntities?.projects) return [];

    const allProjects: ProjectInfo[] = accessibleEntities.projects.map(project => ({
      id: project.id,
      name: project.name,
      companyId: project.company_id,
      companyName: project.company_name
    }));

    if (!searchQuery.trim()) return allProjects;

    const query = searchQuery.toLowerCase();
    return allProjects.filter(
      p => p.name.toLowerCase().includes(query) || p.companyName?.toLowerCase().includes(query)
    );
  }, [accessibleEntities, searchQuery]);

  const handleSelect = (project: ProjectInfo) => {
    onSelect(project);
    onClose();
    setSearchQuery('');
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span>{title}</span>
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ mb: 2 }}>
          <TextField
            fullWidth
            placeholder="Search projects..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            size="small"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon color="action" />
                </InputAdornment>
              )
            }}
          />
        </Box>

        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : projects.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography color="text.secondary">
              {searchQuery ? 'No projects match your search' : 'No projects available'}
            </Typography>
          </Box>
        ) : (
          <List sx={{ maxHeight: 400, overflow: 'auto' }}>
            {projects.map(project => (
              <ListItem key={project.id} disablePadding>
                <ListItemButton onClick={() => handleSelect(project)}>
                  <ListItemIcon>
                    <SolarPowerIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText
                    primary={project.name}
                    secondary={
                      project.companyName && (
                        <Box component="span" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <BusinessIcon sx={{ fontSize: 14 }} />
                          <span>{project.companyName}</span>
                        </Box>
                      )
                    }
                  />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default ProjectPicker;

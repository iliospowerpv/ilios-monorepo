import React, { useState, useMemo } from 'react';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import InputAdornment from '@mui/material/InputAdornment';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import ListSubheader from '@mui/material/ListSubheader';
import { useTheme } from '@mui/material/styles';
import FolderSpecialIcon from '@mui/icons-material/FolderSpecial';
import BusinessIcon from '@mui/icons-material/Business';
import SolarPowerIcon from '@mui/icons-material/SolarPower';
import SearchIcon from '@mui/icons-material/Search';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { useNavigate } from 'react-router-dom';
import { useEntityContext, ScopeType, EntityInfo } from '../../../contexts/entityContext';
import { useAccessibleEntities } from '../../../hooks/useAccessibleEntities';

interface ScopeTabProps {
  scope: ScopeType;
  icon: React.ReactNode;
  label: string;
  isActive: boolean;
  hasSelection: boolean;
  onClick: (event: React.MouseEvent<HTMLButtonElement>) => void;
  showDropdown?: boolean;
}

const ScopeTab: React.FC<ScopeTabProps> = ({ icon, label, isActive, hasSelection, onClick, showDropdown = false }) => {
  const theme = useTheme();

  const getBackgroundColor = () => {
    if (isActive) {
      return theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.08)';
    }
    return 'transparent';
  };

  const getColor = () => {
    if (isActive) {
      return theme.palette.primary.main;
    }
    return theme.palette.text.secondary;
  };

  return (
    <Tooltip title={label} arrow placement="bottom">
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 0.5,
          cursor: 'pointer'
        }}
      >
        <IconButton
          onClick={onClick}
          sx={{
            backgroundColor: getBackgroundColor(),
            color: getColor(),
            borderRadius: '8px',
            padding: '10px',
            transition: 'all 0.2s ease',
            '&:hover': {
              backgroundColor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.16)' : 'rgba(0, 0, 0, 0.12)'
            }
          }}
        >
          {icon}
          {showDropdown && hasSelection && <KeyboardArrowDownIcon sx={{ fontSize: '16px', ml: 0.5 }} />}
        </IconButton>
      </Box>
    </Tooltip>
  );
};

export const EntityContextNav: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const {
    currentScope,
    currentCompany,
    currentProject,
    navigateToScope,
    navigateToCompany,
    navigateToProject,
    getCanonicalPath
  } = useEntityContext();

  const { companies, projects, getProjectsByCompanyId, isLoading } = useAccessibleEntities();

  const [companyAnchorEl, setCompanyAnchorEl] = useState<null | HTMLElement>(null);
  const [projectAnchorEl, setProjectAnchorEl] = useState<null | HTMLElement>(null);
  const [companySearch, setCompanySearch] = useState('');
  const [projectSearch, setProjectSearch] = useState('');

  const companyMenuOpen = Boolean(companyAnchorEl);
  const projectMenuOpen = Boolean(projectAnchorEl);

  const filteredCompanies = useMemo(() => {
    if (!companySearch) return companies;
    const search = companySearch.toLowerCase();
    return companies.filter(c => c.name.toLowerCase().includes(search));
  }, [companies, companySearch]);

  const filteredProjects = useMemo(() => {
    const baseProjects = currentCompany ? getProjectsByCompanyId(currentCompany.id) : projects;

    if (!projectSearch) return baseProjects;
    const search = projectSearch.toLowerCase();
    return baseProjects.filter(
      p => p.name.toLowerCase().includes(search) || p.company_name.toLowerCase().includes(search)
    );
  }, [projects, currentCompany, projectSearch, getProjectsByCompanyId]);

  const handlePortfolioClick = () => {
    navigateToScope('portfolio', { stayInModule: true });
  };

  const handleCompanyClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    if (companies.length === 0) {
      navigate('/companies');
      return;
    }
    setCompanyAnchorEl(event.currentTarget);
  };

  const handleProjectClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    const availableProjects = currentCompany ? getProjectsByCompanyId(currentCompany.id) : projects;

    if (availableProjects.length === 0) {
      if (currentCompany) {
        navigate(`/projects?companyId=${currentCompany.id}`);
      } else {
        navigate('/projects');
      }
      return;
    }
    setProjectAnchorEl(event.currentTarget);
  };

  const handleCompanySelect = (company: { id: number; name: string }) => {
    navigateToCompany({ id: company.id, name: company.name }, { stayInModule: true });
    setCompanyAnchorEl(null);
    setCompanySearch('');
  };

  const handleProjectSelect = (project: { id: number; name: string; company_id: number; company_name: string }) => {
    if (!currentCompany || currentCompany.id !== project.company_id) {
      const companyEntity: EntityInfo = { id: project.company_id, name: project.company_name };
      navigateToCompany(companyEntity, { stayInModule: false });
    }
    navigateToProject({ id: project.id, name: project.name }, { stayInModule: true });
    setProjectAnchorEl(null);
    setProjectSearch('');
  };

  const handleViewCanonical = (scope: ScopeType) => {
    const path = getCanonicalPath(scope);
    navigate(path);
    if (scope === 'company') setCompanyAnchorEl(null);
    if (scope === 'project') setProjectAnchorEl(null);
  };

  const handleCloseCompanyMenu = () => {
    setCompanyAnchorEl(null);
    setCompanySearch('');
  };

  const handleCloseProjectMenu = () => {
    setProjectAnchorEl(null);
    setProjectSearch('');
  };

  const getCompanyLabel = () => {
    if (currentCompany) return currentCompany.name;
    return 'Company';
  };

  const getProjectLabel = () => {
    if (currentProject) return currentProject.name;
    return 'Project';
  };

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        padding: '6px 12px',
        borderRadius: '12px',
        backgroundColor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
        border: `1px solid ${theme.palette.divider}`
      }}
    >
      <ScopeTab
        scope="portfolio"
        icon={<FolderSpecialIcon sx={{ fontSize: '28px' }} />}
        label="Portfolio"
        isActive={currentScope === 'portfolio'}
        hasSelection={true}
        onClick={handlePortfolioClick}
      />

      <ScopeTab
        scope="company"
        icon={<BusinessIcon sx={{ fontSize: '28px' }} />}
        label={getCompanyLabel()}
        isActive={currentScope === 'company'}
        hasSelection={!!currentCompany}
        onClick={handleCompanyClick}
        showDropdown={true}
      />

      <Menu
        anchorEl={companyAnchorEl}
        open={companyMenuOpen}
        onClose={handleCloseCompanyMenu}
        PaperProps={{
          sx: {
            maxHeight: 400,
            width: 300,
            mt: 1
          }
        }}
      >
        <Box sx={{ px: 2, py: 1 }}>
          <TextField
            size="small"
            placeholder="Search companies..."
            value={companySearch}
            onChange={e => setCompanySearch(e.target.value)}
            fullWidth
            autoFocus
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              )
            }}
            onClick={e => e.stopPropagation()}
          />
        </Box>
        <Divider />

        {currentCompany && [
          <MenuItem key="view-company" onClick={() => handleViewCanonical('company')} sx={{ color: 'primary.main' }}>
            <OpenInNewIcon fontSize="small" sx={{ mr: 1 }} />
            <Typography variant="body2">View {currentCompany.name} Overview</Typography>
          </MenuItem>,
          <Divider key="company-divider" />
        ]}

        {isLoading ? (
          <MenuItem disabled>
            <Typography variant="body2" color="text.secondary">
              Loading...
            </Typography>
          </MenuItem>
        ) : filteredCompanies.length === 0 ? (
          <MenuItem disabled>
            <Typography variant="body2" color="text.secondary">
              No companies found
            </Typography>
          </MenuItem>
        ) : (
          filteredCompanies.map(company => (
            <MenuItem
              key={company.id}
              onClick={() => handleCompanySelect(company)}
              selected={currentCompany?.id === company.id}
            >
              <BusinessIcon fontSize="small" sx={{ mr: 1, color: 'text.secondary' }} />
              <Typography variant="body2" noWrap>
                {company.name}
              </Typography>
            </MenuItem>
          ))
        )}
      </Menu>

      <ScopeTab
        scope="project"
        icon={<SolarPowerIcon sx={{ fontSize: '28px' }} />}
        label={getProjectLabel()}
        isActive={currentScope === 'project'}
        hasSelection={!!currentProject}
        onClick={handleProjectClick}
        showDropdown={true}
      />

      <Menu
        anchorEl={projectAnchorEl}
        open={projectMenuOpen}
        onClose={handleCloseProjectMenu}
        PaperProps={{
          sx: {
            maxHeight: 400,
            width: 350,
            mt: 1
          }
        }}
      >
        <Box sx={{ px: 2, py: 1 }}>
          <TextField
            size="small"
            placeholder="Search projects..."
            value={projectSearch}
            onChange={e => setProjectSearch(e.target.value)}
            fullWidth
            autoFocus
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              )
            }}
            onClick={e => e.stopPropagation()}
          />
        </Box>
        <Divider />

        {currentProject && [
          <MenuItem key="view-project" onClick={() => handleViewCanonical('project')} sx={{ color: 'primary.main' }}>
            <OpenInNewIcon fontSize="small" sx={{ mr: 1 }} />
            <Typography variant="body2">View {currentProject.name} Overview</Typography>
          </MenuItem>,
          <Divider key="project-divider" />
        ]}

        {currentCompany && (
          <ListSubheader sx={{ backgroundColor: 'transparent', lineHeight: '32px' }}>
            <Typography variant="caption" color="text.secondary">
              Showing projects for {currentCompany.name}
            </Typography>
          </ListSubheader>
        )}

        {isLoading ? (
          <MenuItem disabled>
            <Typography variant="body2" color="text.secondary">
              Loading...
            </Typography>
          </MenuItem>
        ) : filteredProjects.length === 0 ? (
          <MenuItem disabled>
            <Typography variant="body2" color="text.secondary">
              {currentCompany ? 'No projects in this company' : 'No projects found'}
            </Typography>
          </MenuItem>
        ) : (
          filteredProjects.map(project => (
            <MenuItem
              key={project.id}
              onClick={() => handleProjectSelect(project)}
              selected={currentProject?.id === project.id}
            >
              <Box sx={{ display: 'flex', flexDirection: 'column', minWidth: 0, flex: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <SolarPowerIcon fontSize="small" sx={{ mr: 1, color: 'text.secondary' }} />
                  <Typography variant="body2" noWrap>
                    {project.name}
                  </Typography>
                </Box>
                {!currentCompany && (
                  <Typography variant="caption" color="text.secondary" sx={{ ml: 4 }} noWrap>
                    {project.company_name}
                  </Typography>
                )}
              </Box>
            </MenuItem>
          ))
        )}
      </Menu>
    </Box>
  );
};

export default EntityContextNav;

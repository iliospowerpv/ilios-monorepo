import React from 'react';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import { useTheme } from '@mui/material/styles';
import FolderSpecialIcon from '@mui/icons-material/FolderSpecial';
import BusinessIcon from '@mui/icons-material/Business';
import SolarPowerIcon from '@mui/icons-material/SolarPower';
import { useEntityContext } from '../../../contexts/entityContext';

type EntityLevel = 'portfolio' | 'company' | 'project';

interface NavItemProps {
  level: EntityLevel;
  icon: React.ReactNode;
  label: string;
  isActive: boolean;
  isAvailable: boolean;
  onClick: () => void;
}

const NavItem: React.FC<NavItemProps> = ({ icon, label, isActive, isAvailable, onClick }) => {
  const theme = useTheme();

  const getBackgroundColor = () => {
    if (isActive) {
      return theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.08)';
    }
    return 'transparent';
  };

  const getColor = () => {
    if (!isAvailable) {
      return theme.palette.text.disabled;
    }
    if (isActive) {
      return theme.palette.primary.main;
    }
    return theme.palette.text.secondary;
  };

  return (
    <Tooltip title={isAvailable ? label : `${label} (not selected)`} arrow placement="bottom">
      <span>
        <IconButton
          onClick={onClick}
          disabled={!isAvailable}
          sx={{
            backgroundColor: getBackgroundColor(),
            color: getColor(),
            borderRadius: '8px',
            padding: '10px',
            transition: 'all 0.2s ease',
            '&:hover': {
              backgroundColor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.16)' : 'rgba(0, 0, 0, 0.12)'
            },
            '&.Mui-disabled': {
              color: theme.palette.text.disabled
            }
          }}
        >
          {icon}
        </IconButton>
      </span>
    </Tooltip>
  );
};

export const EntityContextNav: React.FC = () => {
  const theme = useTheme();
  const { currentLevel, currentCompany, currentProject, navigateToLevel } = useEntityContext();

  const handlePortfolioClick = () => {
    navigateToLevel('portfolio');
  };

  const handleCompanyClick = () => {
    if (currentCompany) {
      navigateToLevel('company');
    }
  };

  const handleProjectClick = () => {
    if (currentProject) {
      navigateToLevel('project');
    }
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
      <NavItem
        level="portfolio"
        icon={<FolderSpecialIcon />}
        label="Portfolio"
        isActive={currentLevel === 'portfolio'}
        isAvailable={true}
        onClick={handlePortfolioClick}
      />
      <NavItem
        level="company"
        icon={<BusinessIcon />}
        label={currentCompany ? currentCompany.name : 'Companies'}
        isActive={currentLevel === 'company'}
        isAvailable={!!currentCompany}
        onClick={handleCompanyClick}
      />
      <NavItem
        level="project"
        icon={<SolarPowerIcon />}
        label={currentProject ? currentProject.name : 'Projects'}
        isActive={currentLevel === 'project'}
        isAvailable={!!currentProject}
        onClick={handleProjectClick}
      />
    </Box>
  );
};

export default EntityContextNav;

import * as React from 'react';
import IconButton from '@mui/material/IconButton';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import {
  SidebarContainer,
  SidebarDrawer,
  SidebarHead,
  SidebarToggleButtonContainer,
  SidebarDivider
} from './PageSidebar.styles';
import { CompanyLogo } from '../CompanyLogo/CompanyLogo';
import { NavMenu } from '../NavMenu/NavMenu';
import { useSidebar } from '../../../contexts/sidebar';

export const PageSidebar: React.FC = () => {
  const { isOpen, toggleSidebar } = useSidebar();
  const drawerRef = React.useRef<HTMLDivElement>(null);

  return (
    <SidebarContainer>
      <SidebarDrawer ref={drawerRef} variant="permanent" open={isOpen}>
        <SidebarHead>
          <CompanyLogo />
        </SidebarHead>
        <SidebarDivider />
        <NavMenu containerRef={drawerRef} isMenuOpen={isOpen} />
        <SidebarDivider />
      </SidebarDrawer>
      <SidebarToggleButtonContainer>
        <IconButton sx={{ color: '#7C3AED' }} onClick={toggleSidebar}>
          {isOpen ? <ChevronLeftIcon /> : <ChevronRightIcon />}
        </IconButton>
      </SidebarToggleButtonContainer>
    </SidebarContainer>
  );
};

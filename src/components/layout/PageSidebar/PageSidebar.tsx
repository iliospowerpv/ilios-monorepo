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

export const PageSidebar: React.FC = () => {
  const [open, setOpen] = React.useState(false);
  const drawerRef = React.useRef<HTMLDivElement>(null);

  const toggleDrawer = () => {
    setOpen(!open);
  };

  const closeMenu = () => {
    open && setOpen(false);
  };

  return (
    <SidebarContainer>
      <SidebarDrawer ref={drawerRef} variant="permanent" open={open}>
        <SidebarHead>
          <CompanyLogo />
        </SidebarHead>
        <SidebarDivider />
        <NavMenu containerRef={drawerRef} isMenuOpen={open} closeMenu={closeMenu} />
        <SidebarDivider />
      </SidebarDrawer>
      <SidebarToggleButtonContainer>
        <IconButton color="inherit" onClick={toggleDrawer}>
          {open ? <ChevronLeftIcon /> : <ChevronRightIcon />}
        </IconButton>
      </SidebarToggleButtonContainer>
    </SidebarContainer>
  );
};

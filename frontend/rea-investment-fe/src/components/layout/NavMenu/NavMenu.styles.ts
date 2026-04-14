import { styled } from '@mui/material/styles';
import ButtonBase from '@mui/material/ButtonBase';

export const NavMenuButtonContainer = styled(ButtonBase)(({ theme }) => ({
  width: '100%',
  height: theme.spacing(8),
  backgroundColor: 'rgba(255, 255, 255, 0)',
  borderRadius: 8,
  margin: '2px 8px',
  maxWidth: 'calc(100% - 16px)',
  transition: theme.transitions.create('background-color', {
    easing: theme.transitions.easing.easeInOut,
    duration: theme.transitions.duration.short
  }),
  '& > .MuiGrid-container': {
    color: '#ffffff',
    transition: theme.transitions.create('color', {
      easing: theme.transitions.easing.easeInOut,
      duration: theme.transitions.duration.short
    }),
    '& > .MuiGrid-root > .MuiTypography-root': {
      color: 'rgba(255, 255, 255, 0.7)',
      transition: theme.transitions.create('color', {
        easing: theme.transitions.easing.easeInOut,
        duration: theme.transitions.duration.short
      })
    }
  },
  '&:hover': {
    backgroundColor: 'rgba(156, 158, 243, 0.15)',
    '& > .MuiGrid-container': {
      color: '#9C9EF3',
      '& > .MuiGrid-root > .MuiTypography-root': {
        color: '#ffffff'
      }
    }
  },
  '&.active': {
    backgroundColor: 'color-mix(in srgb, var(--nav-active-color, #9C9EF3) 20%, transparent)',
    '& > .MuiGrid-container': {
      color: 'var(--nav-active-color, #9C9EF3)',
      '& > .MuiGrid-root > .MuiTypography-root': {
        color: 'var(--nav-active-color, #9C9EF3)'
      }
    }
  },
  '&.Mui-disabled > .MuiGrid-container': {
    color: 'rgba(255, 255, 255, 0.3)',
    '& > .MuiGrid-root > .MuiTypography-root': {
      color: 'rgba(255, 255, 255, 0.3)'
    }
  }
}));

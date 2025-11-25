import { styled } from '@mui/material/styles';
import ButtonBase from '@mui/material/ButtonBase';

export const NavMenuButtonContainer = styled(ButtonBase)(({ theme }) => ({
  width: '100%',
  height: theme.spacing(8),
  backgroundColor: 'rgba(255, 255, 255, 0)',
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
      color: '#ffffffb2',
      transition: theme.transitions.create('color', {
        easing: theme.transitions.easing.easeInOut,
        duration: theme.transitions.duration.short
      })
    }
  },
  '&:hover': {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    '& > .MuiGrid-container': {
      color: '#6cc469',
      '& > .MuiGrid-root > .MuiTypography-root': {
        color: '#ffffff'
      }
    }
  },
  '&.active > .MuiGrid-container': {
    color: '#6cc469',
    '& > .MuiGrid-root > .MuiTypography-root': {
      color: '#ffffff'
    }
  },
  '&.Mui-disabled > .MuiGrid-container': {
    color: 'rgba(255, 255, 255, 0.4)',
    '& > .MuiGrid-root > .MuiTypography-root': {
      color: 'rgba(255, 255, 255, 0.4)'
    }
  }
}));

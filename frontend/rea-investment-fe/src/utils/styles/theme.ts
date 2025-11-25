import { createTheme } from '@mui/material/styles';
declare module '@mui/material/styles' {
  interface Theme {
    efficiencyColors: {
      none: string;
      low: string;
      mediocre: string;
      good: string;
      outstanding: string;
    };
    alertSeverity: {
      warning: string;
      high: string;
      severe: string;
    };
    color: {
      blueGray: string;
      red: string;
      black: string;
    };
  }
  interface ThemeOptions {
    efficiencyColors: {
      none: string;
      low: string;
      mediocre: string;
      good: string;
      outstanding: string;
    };
    alertSeverity: {
      warning: string;
      high: string;
      severe: string;
    };
    color: {
      blueGray: string;
      red: string;
      black: string;
    };
  }
}

const theme = createTheme({
  typography: {
    fontFamily: 'Lato, sans-serif',
    button: {
      textTransform: 'none',
      fontWeight: 700
    }
  },
  palette: {
    primary: {
      main: '#1D1D1D'
    },
    secondary: {
      main: '#F9F9F9'
    },
    text: {
      disabled: '#B3B3B3',
      secondary: '#4F4F4F'
    },
    background: {
      default: '#FAFAFA'
    }
  },
  color: {
    blueGray: '#607d8b',
    red: '#B02E0C',
    black: '#1D1D1D'
  },
  shape: {
    borderRadius: 0
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#FFFFFF'
        }
      }
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 0
        },
        sizeMedium: {
          height: '40px'
        }
      }
    }
  },
  efficiencyColors: {
    none: '#E0E0E0',
    low: '#F1B8B6',
    mediocre: '#FAE353',
    good: '#8CD88A',
    outstanding: '#86D0FD'
  },
  alertSeverity: {
    warning: '#F4D918',
    high: '#B02E0C',
    severe: '#5F1513'
  }
});

export default theme;

import { createTheme } from '@mui/material/styles';

type PaletteMode = 'light' | 'dark';

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

export const getTheme = (mode: PaletteMode) => {
  const isLight = mode === 'light';

  return createTheme({
    typography: {
      fontFamily: 'Lato, sans-serif',
      button: {
        textTransform: 'none',
        fontWeight: 700
      }
    },
    palette: {
      mode,
      primary: {
        main: isLight ? '#1D1D1D' : '#FFFFFF'
      },
      secondary: {
        main: isLight ? '#F9F9F9' : '#2D2D2D'
      },
      text: {
        primary: isLight ? '#1D1D1D' : '#FFFFFF',
        secondary: isLight ? '#4F4F4F' : '#B3B3B3',
        disabled: '#B3B3B3'
      },
      background: {
        default: isLight ? '#FAFAFA' : '#121212',
        paper: isLight ? '#FFFFFF' : '#1E1E1E'
      },
      divider: isLight ? 'rgba(0, 0, 0, 0.12)' : 'rgba(255, 255, 255, 0.12)'
    },
    color: {
      blueGray: '#607d8b',
      red: '#B02E0C',
      black: isLight ? '#1D1D1D' : '#FFFFFF'
    },
    shape: {
      borderRadius: 0
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            backgroundColor: isLight ? '#FFFFFF' : '#121212',
            color: isLight ? '#1D1D1D' : '#FFFFFF'
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
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: 'none'
          }
        }
      },
      MuiCard: {
        styleOverrides: {
          root: {
            backgroundColor: isLight ? '#FFFFFF' : '#1E1E1E'
          }
        }
      },
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundColor: isLight ? '#FFFFFF' : '#1E1E1E'
          }
        }
      },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            backgroundColor: isLight ? '#1D1D1D' : '#0A0A0A'
          }
        }
      },
      MuiTableCell: {
        styleOverrides: {
          root: {
            borderColor: isLight ? 'rgba(0, 0, 0, 0.12)' : 'rgba(255, 255, 255, 0.12)'
          }
        }
      },
      MuiDialog: {
        styleOverrides: {
          paper: {
            backgroundColor: isLight ? '#FFFFFF' : '#1E1E1E'
          }
        }
      },
      MuiMenu: {
        styleOverrides: {
          paper: {
            backgroundColor: isLight ? '#FFFFFF' : '#1E1E1E'
          }
        }
      },
      MuiTooltip: {
        styleOverrides: {
          tooltip: {
            backgroundColor: isLight ? '#1D1D1D' : '#424242'
          }
        }
      },
      MuiInputBase: {
        styleOverrides: {
          root: {
            backgroundColor: isLight ? '#FFFFFF' : '#2D2D2D'
          }
        }
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: {
            '& .MuiOutlinedInput-notchedOutline': {
              borderColor: isLight ? 'rgba(0, 0, 0, 0.23)' : 'rgba(255, 255, 255, 0.23)'
            }
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
};

const theme = getTheme('light');

export default theme;

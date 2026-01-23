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
    custom: {
      accent: {
        main: string;
        active100: string;
        active50: string;
      };
      surface: {
        inputs: string;
        lightweight: string;
        cards: string;
      };
      table: {
        rowDefault: string;
        rowHover: string;
        header50: string;
        header100: string;
        header300: string;
      };
      interactive: {
        main: string;
        hover: string;
        highContrast: string;
      };
      gradient: {
        ctaDefault: string;
        ctaHover: string;
        avatar: string;
      };
      icons: {
        accent: string;
        dark: string;
        default: string;
        sidebar: string;
      };
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
    custom?: {
      accent?: {
        main: string;
        active100: string;
        active50: string;
      };
      surface?: {
        inputs: string;
        lightweight: string;
        cards: string;
      };
      table?: {
        rowDefault: string;
        rowHover: string;
        header50: string;
        header100: string;
        header300: string;
      };
      interactive?: {
        main: string;
        hover: string;
        highContrast: string;
      };
      gradient?: {
        ctaDefault: string;
        ctaHover: string;
        avatar: string;
      };
      icons?: {
        accent: string;
        dark: string;
        default: string;
        sidebar: string;
      };
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
        main: isLight ? '#000000' : '#FFFFFF',
        dark: '#4F4F4F',
        light: '#B3B3B3',
        contrastText: isLight ? '#FFFFFF' : '#000000'
      },
      secondary: {
        main: '#20AFE3',
        dark: '#039AD3',
        light: '#20AFE3',
        contrastText: '#FFFFFF'
      },
      text: {
        primary: isLight ? '#000000' : '#FFFFFF',
        secondary: isLight ? '#4F4F4F' : 'rgba(255, 255, 255, 0.6)',
        disabled: '#B3B3B3'
      },
      background: {
        default: isLight ? '#FFFFFF' : '#1A1C27',
        paper: isLight ? '#FFFFFF' : '#1F1F1F'
      },
      error: {
        main: isLight ? '#E53C10' : '#EF3E10',
        dark: isLight ? '#E53C10' : '#EF3E10',
        light: isLight ? '#ED635E' : '#EF3E10',
        contrastText: '#FFFFFF'
      },
      warning: {
        main: '#F4D918',
        dark: isLight ? '#F4D918' : '#CCB514',
        light: '#F4D918'
      },
      success: {
        main: '#6CC469',
        dark: '#6CC469',
        light: '#A7F5A3'
      },
      divider: isLight ? '#323232' : '#79797A',
      action: {
        active: isLight ? 'rgba(0, 0, 0, 0.54)' : 'rgba(255, 255, 255, 0.54)',
        hover: isLight ? 'rgba(0, 0, 0, 0.04)' : 'rgba(255, 255, 255, 0.04)',
        selected: isLight ? 'rgba(0, 0, 0, 0.08)' : 'rgba(255, 255, 255, 0.08)',
        disabled: isLight ? 'rgba(0, 0, 0, 0.26)' : 'rgba(255, 255, 255, 0.26)',
        disabledBackground: isLight ? 'rgba(0, 0, 0, 0.12)' : 'rgba(255, 255, 255, 0.12)',
        focus: isLight ? 'rgba(0, 0, 0, 0.12)' : 'rgba(255, 255, 255, 0.12)'
      }
    },
    color: {
      blueGray: '#607d8b',
      red: '#B02E0C',
      black: isLight ? '#000000' : '#FFFFFF'
    },
    custom: {
      accent: {
        main: isLight ? '#5A5DEB' : '#9C9EF3',
        active100: isLight ? '#DEDFFB' : '#2A2C4D',
        active50: isLight ? '#EEEFFD' : '#36374D'
      },
      surface: {
        inputs: isLight ? '#EEEFFD' : '#3F3B57',
        lightweight: isLight ? '#F7F7F7' : '#242424',
        cards: isLight ? '#FFFFFF' : '#1F1F1F'
      },
      table: {
        rowDefault: isLight ? '#FFFFFF' : '#1F1F1F',
        rowHover: isLight ? '#F5F5F5' : '#333333',
        header50: isLight ? '#F0F0F0' : '#AFB1F3',
        header100: isLight ? '#E3E3E3' : '#9C9EF3',
        header300: isLight ? '#404251' : '#7678E5'
      },
      interactive: {
        main: isLight ? '#494BC1' : '#9C9EF3',
        hover: isLight ? '#3638A0' : '#7B7DEF',
        highContrast: '#0005EB'
      },
      gradient: {
        ctaDefault: 'linear-gradient(87deg, #8D4BE9 0%, #456CF3 100%)',
        ctaHover: 'linear-gradient(87deg, #7F33E9 0%, #4245EB 100%)',
        avatar: 'linear-gradient(87deg, #C5AFF0 0%, #456CF3 100%)'
      },
      icons: {
        accent: isLight ? '#5A5DEB' : '#9C9EF3',
        dark: '#121212',
        default: isLight ? 'rgba(0, 0, 0, 0.5)' : '#FFFFFF',
        sidebar: '#FFFFFF'
      }
    },
    shape: {
      borderRadius: 8
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            backgroundColor: isLight ? '#FFFFFF' : '#1A1C27',
            color: isLight ? '#000000' : '#FFFFFF'
          }
        }
      },
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            textTransform: 'none',
            fontWeight: 700
          },
          sizeLarge: {
            height: '48px',
            padding: '12px 24px'
          },
          sizeMedium: {
            height: '40px',
            padding: '8px 20px'
          },
          sizeSmall: {
            height: '32px',
            padding: '6px 16px'
          },
          contained: {
            background: 'linear-gradient(87deg, #8D4BE9 0%, #456CF3 100%)',
            color: '#FFFFFF',
            '&:hover': {
              background: 'linear-gradient(87deg, #7F33E9 0%, #4245EB 100%)'
            },
            '&.Mui-disabled': {
              background: isLight ? 'rgba(0, 0, 0, 0.12)' : 'rgba(255, 255, 255, 0.12)',
              color: isLight ? 'rgba(0, 0, 0, 0.26)' : 'rgba(255, 255, 255, 0.26)'
            }
          },
          outlined: {
            borderColor: isLight ? 'rgba(0, 0, 0, 0.12)' : 'rgba(255, 255, 255, 0.36)',
            color: isLight ? '#000000' : '#FFFFFF',
            '&:hover': {
              borderColor: isLight ? '#494BC1' : '#9C9EF3',
              backgroundColor: isLight ? 'rgba(73, 75, 193, 0.04)' : 'rgba(156, 158, 243, 0.04)'
            }
          },
          text: {
            color: isLight ? '#494BC1' : '#9C9EF3',
            '&:hover': {
              color: isLight ? '#3638A0' : '#7B7DEF',
              backgroundColor: 'transparent'
            }
          }
        }
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
            backgroundColor: isLight ? '#FFFFFF' : '#1F1F1F',
            borderRadius: 8
          }
        }
      },
      MuiCard: {
        styleOverrides: {
          root: {
            backgroundColor: isLight ? '#FFFFFF' : '#1F1F1F',
            borderRadius: 8
          }
        }
      },
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundColor: isLight ? '#FFFFFF' : '#201E2B'
          }
        }
      },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            backgroundColor: isLight ? '#1A1C27' : '#201E2B'
          }
        }
      },
      MuiTableCell: {
        styleOverrides: {
          root: {
            borderColor: isLight ? '#E0E0E0' : 'rgba(255, 255, 255, 0.12)'
          },
          head: {
            backgroundColor: isLight ? '#F0F0F0' : '#9C9EF3',
            color: isLight ? '#000000' : '#000000',
            fontWeight: 600
          }
        }
      },
      MuiTableRow: {
        styleOverrides: {
          root: {
            '&:hover': {
              backgroundColor: isLight ? '#F5F5F5' : '#333333'
            }
          }
        }
      },
      MuiDialog: {
        styleOverrides: {
          paper: {
            backgroundColor: isLight ? '#FFFFFF' : '#1F1F1F',
            borderRadius: 12
          }
        }
      },
      MuiMenu: {
        styleOverrides: {
          paper: {
            backgroundColor: isLight ? '#FFFFFF' : '#1F1F1F',
            borderRadius: 8
          }
        }
      },
      MuiTooltip: {
        styleOverrides: {
          tooltip: {
            backgroundColor: isLight ? '#1A1C27' : '#2E2E2E',
            borderRadius: 4
          }
        }
      },
      MuiInputBase: {
        styleOverrides: {
          root: {
            backgroundColor: isLight ? '#EEEFFD' : '#3F3B57',
            borderRadius: 8
          }
        }
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            '& .MuiOutlinedInput-notchedOutline': {
              borderColor: isLight ? 'rgba(0, 0, 0, 0.12)' : 'rgba(255, 255, 255, 0.23)'
            },
            '&:hover .MuiOutlinedInput-notchedOutline': {
              borderColor: isLight ? '#494BC1' : '#9C9EF3'
            },
            '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
              borderColor: isLight ? '#5A5DEB' : '#9C9EF3'
            }
          }
        }
      },
      MuiTextField: {
        styleOverrides: {
          root: {
            '& .MuiInputBase-root': {
              borderRadius: 8
            }
          }
        }
      },
      MuiSelect: {
        styleOverrides: {
          root: {
            borderRadius: 8
          }
        }
      },
      MuiChip: {
        styleOverrides: {
          root: {
            borderRadius: 16
          }
        }
      },
      MuiCheckbox: {
        styleOverrides: {
          root: {
            color: isLight ? 'rgba(0, 0, 0, 0.54)' : 'rgba(255, 255, 255, 0.54)',
            '&.Mui-checked': {
              color: isLight ? '#5A5DEB' : '#9C9EF3'
            }
          }
        }
      },
      MuiRadio: {
        styleOverrides: {
          root: {
            color: isLight ? 'rgba(0, 0, 0, 0.54)' : 'rgba(255, 255, 255, 0.54)',
            '&.Mui-checked': {
              color: isLight ? '#5A5DEB' : '#9C9EF3'
            }
          }
        }
      },
      MuiSwitch: {
        styleOverrides: {
          root: {
            '& .MuiSwitch-switchBase.Mui-checked': {
              color: isLight ? '#5A5DEB' : '#9C9EF3'
            },
            '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
              backgroundColor: isLight ? '#5A5DEB' : '#9C9EF3'
            }
          }
        }
      },
      MuiTabs: {
        styleOverrides: {
          indicator: {
            backgroundColor: isLight ? '#5A5DEB' : '#9C9EF3'
          }
        }
      },
      MuiTab: {
        styleOverrides: {
          root: {
            textTransform: 'none',
            fontWeight: 500,
            '&.Mui-selected': {
              color: isLight ? '#5A5DEB' : '#9C9EF3'
            }
          }
        }
      },
      MuiLink: {
        styleOverrides: {
          root: {
            color: isLight ? '#494BC1' : '#9C9EF3',
            '&:hover': {
              color: isLight ? '#3638A0' : '#7B7DEF'
            }
          }
        }
      },
      MuiPagination: {
        styleOverrides: {
          root: {
            '& .MuiPaginationItem-root': {
              borderRadius: 8
            },
            '& .Mui-selected': {
              backgroundColor: isLight ? '#5A5DEB' : '#9C9EF3',
              color: '#FFFFFF'
            }
          }
        }
      },
      MuiAccordion: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            '&:before': {
              display: 'none'
            }
          }
        }
      },
      MuiAvatar: {
        styleOverrides: {
          root: {
            background: 'linear-gradient(87deg, #C5AFF0 0%, #456CF3 100%)'
          }
        }
      },
      MuiBadge: {
        styleOverrides: {
          colorPrimary: {
            backgroundColor: isLight ? '#5A5DEB' : '#9C9EF3'
          }
        }
      },
      MuiLinearProgress: {
        styleOverrides: {
          root: {
            borderRadius: 4,
            backgroundColor: isLight ? '#EEEFFD' : '#36374D'
          },
          bar: {
            borderRadius: 4,
            background: 'linear-gradient(87deg, #8D4BE9 0%, #456CF3 100%)'
          }
        }
      },
      MuiCircularProgress: {
        styleOverrides: {
          root: {
            color: isLight ? '#5A5DEB' : '#9C9EF3'
          }
        }
      },
      MuiSnackbarContent: {
        styleOverrides: {
          root: {
            backgroundColor: isLight ? '#2E2E2E' : '#2E2E2E',
            borderRadius: 8
          }
        }
      },
      MuiAlert: {
        styleOverrides: {
          root: {
            borderRadius: 8
          }
        }
      },
      MuiIconButton: {
        styleOverrides: {
          root: {
            '&:hover': {
              backgroundColor: isLight ? 'rgba(90, 93, 235, 0.08)' : 'rgba(156, 158, 243, 0.08)'
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

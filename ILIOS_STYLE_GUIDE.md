# iliOS Visual Style Guide

A complete, reusable design system extracted from the iliOS frontend. The app is built on **Material UI (MUI) v5** with a single theme factory as the source of truth, mirrored into plain CSS variables and an AG Grid theme. Everything below uses the exact values from the app.

It supports **light and dark mode**. Each value shows `light / dark`.

---

## 1. Typography

| Property | Value |
|---|---|
| Font family (UI) | `'Lato', sans-serif` |
| Font family (full fallback stack) | `'Lato', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif` |
| Font family (code/mono) | `source-code-pro, Menlo, Monaco, Consolas, 'Courier New', monospace` |
| Loaded weights | 300, 400, 700, 900 (+ italics 300/400/700) |
| Google Fonts import | `https://fonts.googleapis.com/css2?family=Lato:ital,wght@0,300;0,400;0,700;0,900;1,300;1,400;1,700&display=swap` |

**Type scale** — the app keeps MUI's default rem-based scale and only customizes the family and the button. These are MUI's resolved defaults (root = 16px) that the app inherits:

| Role | Size | Weight | Line height |
|---|---|---|---|
| h1 | 6rem (96px) | 300 | 1.167 |
| h2 | 3.75rem (60px) | 300 | 1.2 |
| h3 | 3rem (48px) | 400 | 1.167 |
| h4 | 2.125rem (34px) | 400 | 1.235 |
| h5 | 1.5rem (24px) | 400 | 1.334 |
| h6 / subtitle1 | 1.25rem (20px) | 500 | 1.6 |
| subtitle2 | 0.875rem (14px) | 500 | 1.57 |
| body1 (default) | 1rem (16px) | 400 | 1.5 |
| body2 | 0.875rem (14px) | 400 | 1.43 |
| button | 0.875rem (14px) | **700** | 1.75, `text-transform: none` |
| caption | 0.75rem (12px) | 400 | 1.66 |
| overline | 0.75rem (12px) | 400 | 2.66, uppercase |

> Two intentional overrides vs MUI default: `button.fontWeight = 700` and `button.textTransform = 'none'` (no ALL-CAPS buttons).

---

## 2. Color Palette (exact HEX / RGBA)

### Brand / accent
| Token | Light | Dark |
|---|---|---|
| Accent (primary brand) | `#5A5DEB` | `#9C9EF3` |
| Accent active-100 | `#DEDFFB` | `#2A2C4D` |
| Accent active-50 | `#EEEFFD` | `#36374D` |
| Interactive main (links, outlined btn) | `#494BC1` | `#9C9EF3` |
| Interactive hover | `#3638A0` | `#7B7DEF` |
| Interactive high-contrast | `#0005EB` | `#0005EB` |
| Secondary (cyan) | `#20AFE3` (dark `#039AD3`) | `#20AFE3` |

### Gradients (signature look — used on contained buttons, avatars, progress bars)
| Token | Value |
|---|---|
| CTA default | `linear-gradient(87deg, #8D4BE9 0%, #456CF3 100%)` |
| CTA hover | `linear-gradient(87deg, #7F33E9 0%, #4245EB 100%)` |
| Avatar | `linear-gradient(87deg, #C5AFF0 0%, #456CF3 100%)` |

### Primary / text (MUI `palette.primary` is monochrome; accent lives in `custom`)
| Token | Light | Dark |
|---|---|---|
| primary.main | `#000000` | `#FFFFFF` |
| primary.dark | `#4F4F4F` | `#4F4F4F` |
| primary.light | `#B3B3B3` | `#B3B3B3` |
| text.primary | `#000000` | `#FFFFFF` |
| text.secondary | `#4F4F4F` | `rgba(255,255,255,0.6)` |
| text.disabled | `#B3B3B3` | `#B3B3B3` |

### Backgrounds & surfaces
| Token | Light | Dark |
|---|---|---|
| background.default (body) | `#FFFFFF` | `#1A1C27` |
| background.paper | `#FFFFFF` | `#1F1F1F` |
| surface.cards | `#FFFFFF` | `#1F1F1F` |
| surface.inputs | `#EEEFFD` | `#3F3B57` |
| surface.lightweight | `#F7F7F7` | `#242424` |
| AppBar / header | `#FFFFFF` | `#201E2B` |
| Drawer / sidebar | `#1A1C27` | `#201E2B` |

### Borders & dividers
| Token | Light | Dark |
|---|---|---|
| divider | `rgba(0,0,0,0.12)` | `rgba(255,255,255,0.12)` |
| input border (default) | `rgba(0,0,0,0.12)` | `rgba(255,255,255,0.23)` |
| input border (hover/focus) | `#494BC1` / `#5A5DEB` | `#9C9EF3` |
| table cell border | `#E0E0E0` | `rgba(255,255,255,0.12)` |

### Status / feedback
| Token | Light | Dark |
|---|---|---|
| error.main | `#E53C10` | `#EF3E10` |
| error.light | `#ED635E` | `#EF3E10` |
| warning.main | `#F4D918` | `#F4D918` (dark `#CCB514`) |
| success.main | `#6CC469` | `#6CC469` |
| success.light | `#A7F5A3` | `#A7F5A3` |

### Action states (interaction overlays)
| Token | Light | Dark |
|---|---|---|
| action.hover | `rgba(0,0,0,0.04)` | `rgba(255,255,255,0.04)` |
| action.selected | `rgba(0,0,0,0.08)` | `rgba(255,255,255,0.08)` |
| action.disabled | `rgba(0,0,0,0.26)` | `rgba(255,255,255,0.26)` |
| action.disabledBackground | `rgba(0,0,0,0.12)` | `rgba(255,255,255,0.12)` |

### Domain-specific scales (carry over only if useful)
- **Efficiency:** none `#E0E0E0`, low `#F1B8B6`, mediocre `#FAE353`, good `#8CD88A`, outstanding `#86D0FD`
- **Alert severity:** warning `#F4D918`, high `#B02E0C`, severe `#5F1513`
- **Misc:** blueGray `#607d8b`, red `#B02E0C`

---

## 3. Spacing, Radius, Shadows

| Token | Value |
|---|---|
| Spacing unit | MUI default `8px` base (`theme.spacing(1) = 8px`, `2 = 16px`, `3 = 24px`…) |
| Border radius (global) | `8px` (`theme.shape.borderRadius`) |
| Radius — dialogs | `12px` |
| Radius — chips | `16px` |
| Radius — tooltips, progress bars | `4px` |
| Shadows | MUI default 25-level elevation scale (`theme.shadows[1..24]`). Cards/Paper render flat (`backgroundImage: none`) and rely on elevation props. |

**Card style:** background `surface.cards`, radius `8px`, no background image, elevation from MUI `<Paper elevation>`.

---

## 4. Buttons

Global: `borderRadius: 8`, `textTransform: none`, `fontWeight: 700`.

| Size | Height | Padding |
|---|---|---|
| large | 48px | `12px 24px` |
| medium | 40px | `8px 20px` |
| small | 32px | `6px 16px` |

| Variant | Style |
|---|---|
| **contained** (primary CTA) | background = CTA gradient `linear-gradient(87deg, #8D4BE9 0%, #456CF3 100%)`, text `#FFFFFF`; hover = CTA-hover gradient; disabled bg `rgba(0,0,0,0.12)` / text `rgba(0,0,0,0.26)` |
| **outlined** | border + text `#494BC1` (light) / `#FFFFFF` (dark); hover fills `#494BC1` bg with white text (light) / `rgba(156,158,243,0.15)` (dark) |
| **text** | color `#494BC1` / `#9C9EF3`; hover color `#3638A0` / `#7B7DEF`, transparent bg |

---

## 5. Forms / Inputs

| Element | Style |
|---|---|
| InputBase background | `#EEEFFD` (light) / `#3F3B57` (dark) |
| Radius | `8px` |
| Outlined notch (default) | `rgba(0,0,0,0.12)` / `rgba(255,255,255,0.23)` |
| Outlined notch (hover) | `#494BC1` / `#9C9EF3` |
| Outlined notch (focused) | `#5A5DEB` / `#9C9EF3` |
| Checkbox / Radio (unchecked) | `rgba(0,0,0,0.54)` / `rgba(255,255,255,0.54)` |
| Checkbox / Radio (checked) | `#5A5DEB` / `#9C9EF3` |
| Switch (checked thumb + track) | `#5A5DEB` / `#9C9EF3` |

---

## 6. Navigation / Sidebar / Header / Tables

| Element | Style |
|---|---|
| **AppBar (header)** | bg `#FFFFFF` (light) / `#201E2B` (dark) |
| **Drawer (sidebar)** | bg `#1A1C27` (light) / `#201E2B` (dark) — sidebar is dark even in light mode; sidebar icons `#FFFFFF` |
| **Tabs** | indicator `#5A5DEB` / `#9C9EF3`; selected tab text same; `textTransform: none`, weight 500 |
| **Links** | `#494BC1` / `#9C9EF3`, hover `#3638A0` / `#7B7DEF` |
| **Table header** | bg `#F0F0F0` (light) / `#9C9EF3` (dark), text weight 600 |
| **Table row hover** | `#F5F5F5` / `#333333` |
| **Table selected row** | `#EEEFFD` / `#2A2C4D` |
| **Pagination selected** | bg accent, white text |
| **Avatar** | avatar gradient `linear-gradient(87deg, #C5AFF0 0%, #456CF3 100%)` |
| **Tooltip** | bg `#1A1C27` / `#2E2E2E`, radius 4 |

---

## 7. CSS Variables (framework-agnostic — use these in non-MUI projects)

```css
:root {
  --accent-color: #5A5DEB;
  --accent-light: #DEDFFB;
  --accent-lighter: #EEEFFD;
  --gradient-cta: linear-gradient(87deg, #8D4BE9 0%, #456CF3 100%);
  --gradient-cta-hover: linear-gradient(87deg, #7F33E9 0%, #4245EB 100%);
  --gradient-avatar: linear-gradient(87deg, #C5AFF0 0%, #456CF3 100%);
  --interactive-main: #494BC1;
  --interactive-hover: #3638A0;
  --border-radius: 8px;
}

[data-theme="dark"] {
  --accent-color: #9C9EF3;
  --accent-light: #2A2C4D;
  --accent-lighter: #36374D;
  --interactive-main: #9C9EF3;
  --interactive-hover: #7B7DEF;
}

body {
  margin: 0;
  font-family: 'Lato', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto',
    'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans',
    'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

---

## 8. Tailwind config (if you use Tailwind in the new project)

> The source app does **not** ship a custom `tailwind.config.js` (Tailwind is a dependency but the design lives in MUI). Below is a ready-made config that reproduces the same tokens in Tailwind.

```js
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['class', '[data-theme="dark"]'],
  content: ['./src/**/*.{js,jsx,ts,tsx,html}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Lato', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['source-code-pro', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      colors: {
        accent: { DEFAULT: '#5A5DEB', light: '#DEDFFB', lighter: '#EEEFFD', dark: '#9C9EF3' },
        interactive: { DEFAULT: '#494BC1', hover: '#3638A0', contrast: '#0005EB' },
        secondary: { DEFAULT: '#20AFE3', dark: '#039AD3' },
        surface: { card: '#FFFFFF', input: '#EEEFFD', light: '#F7F7F7', cardDark: '#1F1F1F', inputDark: '#3F3B57' },
        sidebar: '#1A1C27',
        header: '#FFFFFF',
        ink: { DEFAULT: '#000000', secondary: '#4F4F4F', disabled: '#B3B3B3' },
        status: { error: '#E53C10', warning: '#F4D918', success: '#6CC469' },
      },
      borderRadius: { DEFAULT: '8px', lg: '12px', pill: '16px', sm: '4px' },
      backgroundImage: {
        'cta': 'linear-gradient(87deg, #8D4BE9 0%, #456CF3 100%)',
        'cta-hover': 'linear-gradient(87deg, #7F33E9 0%, #4245EB 100%)',
        'avatar': 'linear-gradient(87deg, #C5AFF0 0%, #456CF3 100%)',
      },
    },
  },
  plugins: [],
};
```

---

## 9. Drop-in MUI theme (the real source file — copy this verbatim for an MUI project)

Save as `src/theme.ts` and wrap your app in `<ThemeProvider theme={getTheme('light')}>`. This is the exact theme the app uses.

```ts
import { createTheme } from '@mui/material/styles';

type PaletteMode = 'light' | 'dark';

export const getTheme = (mode: PaletteMode) => {
  const isLight = mode === 'light';

  return createTheme({
    typography: {
      fontFamily: 'Lato, sans-serif',
      button: { textTransform: 'none', fontWeight: 700 },
    },
    palette: {
      mode,
      primary: {
        main: isLight ? '#000000' : '#FFFFFF',
        dark: '#4F4F4F',
        light: '#B3B3B3',
        contrastText: isLight ? '#FFFFFF' : '#000000',
      },
      secondary: { main: '#20AFE3', dark: '#039AD3', light: '#20AFE3', contrastText: '#FFFFFF' },
      text: {
        primary: isLight ? '#000000' : '#FFFFFF',
        secondary: isLight ? '#4F4F4F' : 'rgba(255, 255, 255, 0.6)',
        disabled: '#B3B3B3',
      },
      background: {
        default: isLight ? '#FFFFFF' : '#1A1C27',
        paper: isLight ? '#FFFFFF' : '#1F1F1F',
      },
      error: {
        main: isLight ? '#E53C10' : '#EF3E10',
        dark: isLight ? '#E53C10' : '#EF3E10',
        light: isLight ? '#ED635E' : '#EF3E10',
        contrastText: '#FFFFFF',
      },
      warning: { main: '#F4D918', dark: isLight ? '#F4D918' : '#CCB514', light: '#F4D918' },
      success: { main: '#6CC469', dark: '#6CC469', light: '#A7F5A3' },
      divider: isLight ? 'rgba(0, 0, 0, 0.12)' : 'rgba(255, 255, 255, 0.12)',
    },
    shape: { borderRadius: 8 },
    components: {
      MuiButton: {
        styleOverrides: {
          root: { borderRadius: 8, textTransform: 'none', fontWeight: 700 },
          sizeLarge: { height: '48px', padding: '12px 24px' },
          sizeMedium: { height: '40px', padding: '8px 20px' },
          sizeSmall: { height: '32px', padding: '6px 16px' },
          contained: {
            background: 'linear-gradient(87deg, #8D4BE9 0%, #456CF3 100%)',
            color: '#FFFFFF',
            '&:hover': { background: 'linear-gradient(87deg, #7F33E9 0%, #4245EB 100%)' },
          },
          outlined: {
            borderColor: isLight ? '#494BC1' : 'rgba(255, 255, 255, 0.36)',
            color: isLight ? '#494BC1' : '#FFFFFF',
            '&:hover': {
              borderColor: isLight ? '#494BC1' : '#9C9EF3',
              backgroundColor: isLight ? '#494BC1' : 'rgba(156, 158, 243, 0.15)',
              color: '#FFFFFF',
            },
          },
          text: {
            color: isLight ? '#494BC1' : '#9C9EF3',
            '&:hover': { color: isLight ? '#3638A0' : '#7B7DEF', backgroundColor: 'transparent' },
          },
        },
      },
      MuiPaper: { styleOverrides: { root: { backgroundImage: 'none', borderRadius: 8 } } },
      MuiCard: { styleOverrides: { root: { borderRadius: 8 } } },
      MuiAppBar: { styleOverrides: { root: { backgroundColor: isLight ? '#FFFFFF' : '#201E2B' } } },
      MuiDrawer: { styleOverrides: { paper: { backgroundColor: isLight ? '#1A1C27' : '#201E2B' } } },
      MuiDialog: { styleOverrides: { paper: { borderRadius: 12 } } },
      MuiChip: { styleOverrides: { root: { borderRadius: 16 } } },
      MuiInputBase: {
        styleOverrides: { root: { backgroundColor: isLight ? '#EEEFFD' : '#3F3B57', borderRadius: 8 } },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: isLight ? '#494BC1' : '#9C9EF3' },
            '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: isLight ? '#5A5DEB' : '#9C9EF3' },
          },
        },
      },
      MuiTab: {
        styleOverrides: {
          root: { textTransform: 'none', fontWeight: 500, '&.Mui-selected': { color: isLight ? '#5A5DEB' : '#9C9EF3' } },
        },
      },
      MuiTabs: { styleOverrides: { indicator: { backgroundColor: isLight ? '#5A5DEB' : '#9C9EF3' } } },
      MuiLink: {
        styleOverrides: {
          root: { color: isLight ? '#494BC1' : '#9C9EF3', '&:hover': { color: isLight ? '#3638A0' : '#7B7DEF' } },
        },
      },
      MuiCheckbox: { styleOverrides: { root: { '&.Mui-checked': { color: isLight ? '#5A5DEB' : '#9C9EF3' } } } },
      MuiAvatar: { styleOverrides: { root: { background: 'linear-gradient(87deg, #C5AFF0 0%, #456CF3 100%)' } } },
    },
  });
};

export default getTheme('light');
```

---

## 10. Light/Dark mode toggle (optional — the app persists choice to localStorage)

```tsx
// Wrap your app; reads OS preference, persists to localStorage key 'ilios-theme-mode'.
import { ThemeProvider } from '@mui/material/styles';
import { useState, useEffect, useMemo } from 'react';
import { getTheme } from './theme';

export function AppThemeProvider({ children }) {
  const [mode, setMode] = useState(() => {
    const stored = localStorage.getItem('ilios-theme-mode');
    if (stored === 'light' || stored === 'dark') return stored;
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });
  useEffect(() => { localStorage.setItem('ilios-theme-mode', mode); }, [mode]);
  const theme = useMemo(() => getTheme(mode), [mode]);
  return <ThemeProvider theme={theme}>{children}</ThemeProvider>;
}
```

---

## Quick-start for the new project

1. Add the Lato `@import` (section 7) to your global stylesheet, or `<link>` it in `index.html`.
2. **MUI project:** copy section 9 into `src/theme.ts` and wrap with `ThemeProvider`. Done.
3. **Tailwind project:** copy section 8 into `tailwind.config.js` and the CSS variables from section 7 into your global CSS.
4. **Plain CSS / other framework:** use the CSS variables (section 7) plus the palette tables (section 2).

**Signature elements to keep the look recognizable:** Lato font, the `87deg` purple→blue CTA gradient on primary buttons, `#5A5DEB` accent, `8px` radius everywhere, and the dark sidebar (`#1A1C27`) against light content.

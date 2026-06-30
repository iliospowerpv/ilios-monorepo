---
name: MUI Drawer dark-paper override traps content
description: The global MuiDrawer.paper override paints every Drawer dark even in LIGHT mode, so reused Drawers get light-mode (dark) text on a dark surface — invisible.
---

The FE theme sets `components.MuiDrawer.styleOverrides.paper.backgroundColor` to a DARK
value in BOTH modes (light: `#1A1C27`, dark: `#201E2B`) because the dark left-nav sidebar
reuses `<Drawer>`. Any OTHER feature that mounts a plain `<Drawer>` (e.g. the AI Assistant
panel) silently inherits that dark surface, but its child Typography/Chips use the theme's
light-mode text tokens (`text.primary=#000000`, `text.secondary=#4F4F4F`) → dark text on a
dark panel = unreadable. Nothing in the component is "wrong"; the surface/text mismatch is
the theme override leaking across unrelated Drawers.

**Fix pattern:** wrap the Drawer in a nested `<ThemeProvider theme={getTheme('dark')}>`
(module-level constant, static — don't recreate per render) so all descendants resolve the
dark palette's LIGHT text/input/chip colors against the dark paper. React context propagates
through MUI's Drawer Portal, so the nested theme reaches the portaled content. Prefer this
over patching each child's `color=` — it's one change and covers future children. Add
`color: 'text.primary'` on the Drawer PaperProps sx as an inheritance belt-and-suspenders.

**Why:** the override is global and shared with navigation; you cannot just "make the Drawer
light" without breaking the sidebar. Re-theming only the offending panel is the safe scope.

**How to apply:** any time you add/reuse a bare `<Drawer>` for content (not the left nav),
assume the paper is dark and give it a dark theme context, or text will vanish in light mode.
In app dark mode this wrap is a neutral no-op (same dark palette semantics).

---
name: MUI primary.main surface legibility (iliOS FE)
description: Why controls on a primary.main background go invisible in iliOS, and how to keep them legible across theme modes.
---

# Controls on a `primary.main` surface must set explicit colors

In the iliOS frontend theme, `palette.primary.main` is **solid black (`#000000`) in light mode** and **white (`#FFFFFF`) in dark mode**. Several headers use `bgcolor: 'primary.main'` (e.g. the Data Room Document Details modal `DialogTitle`).

MUI's *default* disabled/faint styling — disabled `Button` text/fill (`rgba(0,0,0,0.26)` / `rgba(0,0,0,0.12)`) and near-transparent greys like `#00000042` — are **invisible** against that black header (and would invert-fail on the white dark-mode header).

**Why:** a "completed" disabled button on the black header showed only its (color-forced) green check icon — the "Promoted" label and button surface were black-on-black.

**How to apply:** any icon/label/border placed on a `primary.main` surface must use an explicit color that contrasts with BOTH black and white (e.g. the health-indicator green `theme.efficiencyColors.good`/`#4CAF50`, or a solid mid grey `#9e9e9e` — NOT `#00000042`). For disabled MUI buttons there, override `&.Mui-disabled` (set `opacity:1`, explicit `color`, `backgroundColor`, `borderColor`) rather than relying on defaults. Prefer an outlined-chip look (transparent bg + colored border + colored text/icon) so it reads in both modes; reserve `border:'1px solid transparent'` on the base so the active↔disabled swap doesn't shift layout.

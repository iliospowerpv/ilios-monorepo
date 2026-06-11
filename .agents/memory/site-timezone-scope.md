---
name: Site timezone scope
description: What the per-Site IANA timezone is (and isn't) used for across the iliOS REA platform.
---

# Site timezone scope

A Site carries an IANA `timezone` (additive `sites.timezone` column, NOT NULL,
default `UTC`). It governs **only site-local telemetry computations** — chiefly
the daily/"today" production boundary. It is **not** a display setting.

**Rule:**
- All timestamp DISPLAY across the app stays in the viewer's browser timezone
  (parse naive-UTC by appending `Z`, then `toLocaleString()`).
- Use `site.timezone` only to compute site-local calendar boundaries for
  telemetry/reporting (e.g. "today" = the site's local day).
- Telemetry readings/rollups are stored **naive-UTC**, so a site-local boundary
  must be converted: `datetime.now(ZoneInfo(site.timezone)).replace(midnight)
  .astimezone(utc).replace(tzinfo=None)`. Fall back to UTC + log on missing/invalid tz.

**Why:** The product intentionally keeps display viewer-local (a portfolio spans
many timezones; users expect their own clock), but day-bucketed production math
("today's kWh", daily irradiance alignment) is only correct against the site's
local day. Conflating the two silently shifts daily totals by the UTC offset.

**How to apply:** When adding any telemetry/reporting computation that buckets by
day (or aligns to local sunrise/etc.), reach for `site.timezone` + the
local-midnight→naive-UTC conversion — never the browser tz, and never reuse
`site.timezone` for formatting timestamps shown to users.

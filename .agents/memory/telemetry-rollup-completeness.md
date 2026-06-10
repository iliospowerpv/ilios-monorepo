---
name: Telemetry rollup completeness cadence
description: Why interval-rollup completeness must infer sampling cadence per-series, not per-metric
---

Rollup `completeness` = `sample_count / expected`, where `expected = bucket_seconds / inferred_cadence` (clamped ≤1, None when cadence can't be inferred). Cadence is the median gap between a series' distinct timestamps.

**Rule:** Infer cadence **per series** (per `(device|site-sentinel, metric)`), never per-metric by merging timestamps across all devices.

**Why:** Multiple devices report the same metric on offset schedules. Merging their timestamps interleaves those schedules into a tiny median gap (~1s instead of the true ~900s), which massively overstates `expected` and produces pathological completeness (~0.009 for full buckets). Caught live on site 4: `device_power_ac_kw` (8 devices) read ~0.009 with the merged approach, ~0.85–1.0 once split per-series.

**How to apply:** Device-level completeness uses that device's own series cadence (falling back to the per-metric median of series cadences). Site-level completeness sums each *contributing* series' own expected count for the bucket so mixed-cadence series compose correctly. The site-level sentinel for `device_id IS NULL` rows must be an id real devices can't take (device PKs start at 1, so `0` is safe).

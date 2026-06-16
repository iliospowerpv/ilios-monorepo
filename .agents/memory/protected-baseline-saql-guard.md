---
name: Protected baseline-driving SAFL write guard
description: How Project Hub Overview keeps baseline-driving fields read-only/no-BQ, and the invariant that keeps the BigQuery sync a no-op.
---

# Protected baseline-driving field guard (Project Hub Overview)

Some Overview fields are "baseline-driving" and owned by the Data Room / promoted
project-facts provenance chain, NOT by the site-details edit form: the four ohmic
losses (`dc_wiring_loss`, `ac_wiring_loss`, `medium_voltage_loss`, `mv_line_loss`)
on `asset_overview`, and `permission_to_operate` (PTO) on `key_dates`. They are
rendered read-only with provenance labels and must never be written through the
site-details edit form.

## How the guard works
The `update_site_details` endpoint looks up `PROTECTED_BASELINE_DRIVING_FIELDS[section]`
(in `app/static/sites.py`) and **deletes** those keys from the validated payload
before persisting. The remaining keys go to the SAFL update AND to the
`SiteCharacteristicsHandler` BigQuery background task as the SAME stripped dict.

**Why delete the key instead of setting `None`:** SQLAlchemy `query.update(item)`
only writes keys present in `item`. Deleting the key preserves the existing SAFL
value; setting `None` would explicitly blank the column.

## The invariant that keeps BigQuery a no-op
The BQ no-op guarantee holds ONLY because `SiteCharacteristicsHandler.sync_to_bq`
is **diff-input-driven** — it diffs `new_record` (the stripped dict) vs `old_record`
and returns before initializing any BigQuery engine when there are zero changed
fields. The handler maps only protected/BQ-owned characteristic fields, so once
those are stripped the diff is empty.

**Why this matters:** if future code ever makes `sync_to_bq` read the full live DB
row instead of the passed `new_record`, this guard silently breaks and protected
fields could re-enter BigQuery. Keep the handler diff-input-only.

## Scope limits
- The guard is **endpoint-local** to `update_site_details`. Other SAFL write paths
  (imports, migrations, scripts, direct CRUD) are NOT protected by it.
- Phase 1+2 is labeling + write-guarding only. Reads are NOT rebound to
  `project_facts` (that is Phase 3). SAFL is never used as a V2 baseline source.

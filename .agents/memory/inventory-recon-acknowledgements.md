---
name: Inventory reconciliation acknowledgements
description: How reviewer "sign-off" on Device Inventory Reconciliation mismatches is modeled (binding, policy gating, expired state, ladder).
---

# Inventory Reconciliation acknowledgements (reviewer sign-off)

Reviewers (Asset.edit) can acknowledge actionable Device Inventory Reconciliation
mismatches; this unlocks ladder state G6 `mapping_complete_with_acknowledged_exceptions`.

**Rule:** an acknowledgement binds to BOTH the exact `mismatch_signature` AND the
`reconciliation_version` (currently `"inv-recon/1"`, a constant in the recon
service). If recon logic changes the version, prior acks become read-time
"expired" — the DB enum intentionally stays `{acknowledged, revoked}` only;
"expired" is derived, never stored.

**Why:** an ack is a statement about a specific observed discrepancy under a
specific reconciliation interpretation. If either the discrepancy fingerprint or
the reconciliation logic changes, the old sign-off must NOT silently keep
suppressing a now-different mismatch.

**How to apply:**
- Acknowledgeable ONLY when `acknowledgement_policy` is `acknowledgeable_*`.
  `not_acknowledgeable_blocking` (e.g. Site-4 unsatisfied weather dependency) can
  NEVER be acknowledged — enforced server-side (422), not just hidden in UI.
- Strictly additive: the feature never mutates devices, mappings, project_facts,
  telemetry_*, weather_device_mappings, or baselines. It only writes the ack table.
- The recon service re-derives the live mismatch on write and snapshots it; the
  endpoint returns 404 (unknown signature), 409 (stale version OR double-ack),
  422 (non-acknowledgeable policy).
- `acknowledged_exception_count` / `open_actionable_mismatch_count` are recon
  tallies that already account for active acks; G6 is reachable only when every
  remaining actionable mismatch is acknowledged.
- FE permission key is `'Asset Management'` (display name, not snake_case).

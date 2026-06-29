---
name: Native workflow onboarding orchestration (read-only advice layer)
description: Boundary + gotchas for the guided-onboarding/AI-orchestration layer built on the native workflow engine.
---

# Native workflow onboarding orchestration

The native workflow engine has a **read-only aggregation/advice layer** on top of the write-handshake
engine: guided sequences (declarative composition of existing workflows + cross-step prefill hints),
per-project onboarding progress + readiness rollups, deterministic next-action recommendations, and a
single versioned orchestration-context envelope (`mode="read_only_advice"` + machine-readable
`prohibited_actions[]`) meant for a FUTURE AI advisor.

## Durable invariants (don't regress)
- The advice layer **never** writes/commits, starts/advances a run, or performs a governed action
  (fact promotion, baseline activation, device mapping, weather declaration). Those stay exclusive to
  the human-authorized handshake and are listed in `prohibited_actions`.
- Rollups **read existing service verdicts verbatim** — never recompute. A dimension the caller can't
  see or that errors degrades to `available=false`/reason and is **excluded from completion ratios**;
  it is never rendered as a 0%/failing state.
- Sequences/prefill grant **no authority**: a prefill hint is a UI seed only; the per-step workflow
  re-validates + re-authorizes its inputs at execute time.

## Gotcha: gate advice on the TARGET action's permission, not the signal's read permission
A recommendation/advice surface must check the permission the **recommended action** actually needs,
not the (looser) read permission that made the signal visible.

**Why:** the `document_upload` recommendation was first gated only on the onboarding progress stage
being evaluable (which needs Diligence **`view`**) + a coarse `_can_start_workflow`. But uploading
needs Diligence **`edit`** on that specific site, so a view-only-but-not-editable project produced a
dead-end card. Fixed by also requiring the target site be in `_diligence_editable_site_ids` (the same
resolver the upload *options* use). `None` from that resolver == platform-bypass == all sites.

**How to apply:** when adding any new recommendation/deep-link, gate it on the destination action's
own per-target permission (reuse the resolver that the action's option-list/prerequisite uses), not
merely on whether the surfacing read succeeded.

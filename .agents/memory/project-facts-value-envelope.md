---
name: project_facts.value {"v":...} envelope
description: Every consumer of project_facts.value must unwrap the {"v": scalar} JSONB envelope; raw reads fail closed to missing.
---

# `project_facts.value` is a `{"v": <scalar>}` JSONB envelope

`project_facts.value` is **always** stored wrapped, e.g. `{"v": "7"}` / `{"v": "1900"}`
— note the inner scalar is often a *string*, even for numeric fields. The DD
reconciliation service exposes the canonical unwrap (`_unwrap(value)` →
`value["v"]`).

**Rule:** any new consumer that reads a documented fact value MUST unwrap first
(`_coerce_int(_unwrap(fact.value))`, `_as_text(_unwrap(fact.value))`). Reading
`fact.value` raw hands a `dict` to int/text coercers, which **fail closed to
`None`** — the documented value silently reads as *missing* rather than erroring.

**Why:** a read-only consumer that "fails closed to missing" produces a plausible-
looking result, so the bug is invisible unless a test/validation asserts the actual
numeric value.

**How to apply / validation trap:** a headline/aggregate that can be reached by a
path *not depending on the numeric value* (e.g. a blocking weather dependency that
wins the status ladder regardless of counts) will MASK a raw-read regression during
manual/site validation. Always add a test that asserts the unwrapped documented
count itself (not just the headline), and grep new fact-value reads for a missing
`_unwrap`.

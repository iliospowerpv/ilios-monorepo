---
name: DD V2 extraction-registry seeding (generic + specialized coexistence)
description: Invariants and footguns when seeding the extraction_registry (generic eligibility for all doc types + specialized schema versions) via Alembic data migrations.
---

# Extraction registry: generic vs specialized coverage

The `extraction_registry` powers in-app DD parsing. Two tiers of coverage coexist and MUST NOT clobber each other:

- **Specialized** (~17 doc types) seeded from `ai_parsing_config.json` via `dev_scripts/seed_extraction_registry.py` — each has an active schema (rich, doc-specific fields) + active prompt. Their schema/prompt `notes` are the config-seed strings.
- **Generic** coverage (DD V2 Phase 1B) makes EVERY `SiteDocumentsEnum` doc type parse-eligible: `is_parsable=true` + an active generic schema (small set of generic canonical fields) + active generic prompt — added **only where no active schema/prompt already exists**.

**The dedupe mechanism is normalized-name matching.** `normalize(display_name)` (lower, strip non-alnum/space, spaces→`_`) of a `SiteDocumentsEnum` display name equals the existing specialized row's `name`, so a SELECT-by-name before insert skips the 17 specialized types. If you ever change the normalization, the generic seeder will stop recognizing the specialized rows and double-seed them. Keep `app/services/extraction_registry_seeding.py` normalization identical to the dev seed script.

**Why:** the whole design lets specialized fields always win for the doc types that have them, while everything else still gets a usable generic extraction path. Resolution at parse time is "active schema + active prompt" via the CRUD active-getters, so coexistence is safe as long as each doc type has exactly one active of each.

## Footgun: raw Core `text()` inserts in migrations don't apply client-side `default=`
These models mix `default=` (client/ORM-side, NOT applied by `connection.execute(text(...))`) and `server_default=`. When seeding via Core in a migration you MUST supply every NOT-NULL column that lacks a `server_default`, e.g. `extraction_document_types.category`, `extraction_schema_version_fields.is_required/extraction_priority`, `extraction_prompt_templates.extraction_prompt/model_name/temperature/max_tokens`. `created_at/updated_at` (and a few like `canonical_fields.field_type/is_active`) DO have server defaults. Omitting a client-`default=` column → NOT NULL violation at insert time, not at model definition.

## PVsyst specialized v2 (Phase 1C)
The As-Built (Second Buyer) PVsyst report is the baseline-input document. Its specialized v2 schema is built by **cloning v1's field links** (so no display-name key is ever lost) and marking the 16 `DueDiligenceBQKeys` baseline-driving fields `is_required`, then flipping `is_active` (deactivate v1, activate v2). v1 rows are never mutated. Seeding is idempotent via marker `notes`; re-run is a no-op.

## The "generic" tier is specifically CONTRACTUAL — wrong for equipment/datasheet/PTO types
The generic schema is not a neutral small fieldset — it is the **contractual** 10-field set (`document_title, document_date, counterparties, effective_date, expiration_or_termination_date, term_or_duration, key_obligations, key_amounts_or_fees, governing_law_or_jurisdiction, summary`) under a generic "document extraction specialist" prompt. **201 of 218 doc types share it** (only the ~17 specialized escape it). So `module_specs`/`inverter_specs`/`*_warranty`/`transformer_specs`/`storage_specs`/`battery_specs`/`racking_specs`/PTO/COD all resolve to contractual extraction.

**`is_parsable=true` is NOT evidence of equipment-specific intelligence.** All 218 types report parsable+active+has-schema+has-prompt, so the registry "looks supported" while equipment datasheets have no equipment fields (`module_wattage`, `thermal_coefficient_pct`, `inverter_ac_power_kw`, etc. don't exist as canonical fields). An empty Data Room for a datasheet is usually (a) no parse run ever fired AND (b) even if it did, it would extract contractual fields. **Why:** future equipment-parsing work must add real canonical fields + schemas + an equipment-aware prompt, not just rely on the type being registered. Full analysis: `docs/equipment_datasheet_parsing_and_governed_baseline_field_coverage_audit.md`.

## Override guardrail: status-gated API bypass is CLOSED
The status-gated bypass is closed on BOTH endpoints — `set_key` and `bulk_accept_ai_values` now detect baseline-driving value divergence SERVER-SIDE (via the shared `override_guardrail.py` helper) and force the override-rationale path regardless of client status; bulk is all-or-nothing (422 writes nothing). See `dd-override-guardrail.md` for the design.

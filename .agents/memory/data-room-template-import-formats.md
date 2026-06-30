---
name: Data Room template import formats
description: Data Room template import accepts JSON or CSV; both must stay fail-closed through the same shared validator, templates stay immutable/creation-only.
---

Data Room template **import** supports two mutually-exclusive source formats on the
same `/import` endpoint: a JSON `payload` (object) or a `csv` (flat string). The
request schema enforces **exactly one of** `payload`/`csv`.

**Rule:** every import source must funnel through the one shared structural validator
(`validate_template_structure`) before a template row is created. Never let a new
import source (e.g. a future XLSX/Sheets path) build the nested structure and skip
that validator — it is the single fail-closed gate (unknown section keys / doc kinds,
duplicate section keys, duplicate doc kinds per section, non-bool `required` all
rejected). Semantic validation lives server-side, NOT in the frontend.

**Why:** keeps all formats honest and identical in behavior, and preserves the core
invariant — applying/importing a template is a **creation** of an immutable snapshot,
never a sync/reconcile of an existing Data Room.

**CSV gotcha:** spreadsheet exports (Excel / Google Sheets) prefix a UTF-8 BOM
(`\ufeff`) on the first header cell, which silently breaks required-column detection.
Strip a single leading BOM before parsing. Unknown/extra CSV columns are intentionally
ignored (spreadsheet tolerance), not rejected.

**How to apply:** when adding any new template import format, add a parser that emits
the nested structure and route it through `validate_template_structure`; add the new
field to the import schema's exactly-one-of validator; keep the router branch additive
so the existing JSON path is untouched.

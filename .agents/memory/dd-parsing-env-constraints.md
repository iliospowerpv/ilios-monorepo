---
name: DD in-app parsing environment constraints
description: Two container-level blockers that stop live in-app DD document parsing here, independent of parsing code.
---

# DD in-app parsing — environment constraints (this Replit container)

Two blockers can stop a *live* in-app parse even when the parsing code is correct. Both are
environment/ops conditions, not code defects.

## 1. AES-encrypted PDFs cannot be text-extracted
- `pypdf` needs **either** `cryptography` **or** `pycryptodome` for the AES crypt provider.
  Here **both are absent**, so pypdf falls back to `local_crypt_fallback` and raises
  `[text_extraction_failed] ... cryptography>=3.1 is required for AES algorithm`.
- **Neither can be installed in this container.** The Nix store is immutable, so `uv add`
  (the package-management tool) fails with a permission-denied writing to `/nix/store/...`,
  and `pip install --user` is disabled by PEP 668 ("modify the immutable /nix/store").
- **How to apply:** if a DD fixture/file fails with the AES message, it is owner/AES-encrypted
  and unrecoverable here — it is NOT a schema/prompt bug. Non-encrypted PDFs extract fine.
  Validate that fixture's expected shape with a deterministic unit test instead of a live parse.

## 2. Seeded prompt templates used a gateway-unsupported model (now fixed + self-healing)
- History: essentially every auto-seeded `extraction_prompt_templates` row declared
  `model_name = "claude-sonnet-4-5"`, which the Replit AI gateway rejects with
  `UNSUPPORTED_MODEL`. This was **registry-wide**, so nearly every document type failed every
  parse run with `[llm_call_failed] ... 400 UNSUPPORTED_MODEL`, not just one doc type.
- Fix applied (durable + registry-wide): `in_app_parsing_service.call_llm` now treats only
  `gpt-5*`/`gpt-4.1*` as supported and remaps **anything else** (incl. `claude-*`, `gpt-4o`) →
  `gpt-5.2` (logging a warning). So a stale/unsupported configured model can no longer 400 a run.
  All source defaults were repointed to `gpt-5.2` (`GENERIC_MODEL_NAME`, the `model_name` column
  default, the CRUD/router create defaults, the dev seed), and the live `extraction_prompt_templates`
  rows were UPDATEd off `claude-sonnet-4-5` → `gpt-5.2`.
- **Why:** model availability is a gateway/ops fact, so the parser must self-heal an unsupported
  configured model name rather than hard-fail — config drift should never block parsing.
- **How to apply:** if `UNSUPPORTED_MODEL` ever reappears, the gateway dropped a model the guard
  still treats as supported — update the supported-prefix allowlist in `call_llm`, don't special-case
  one template. Verified live: file 27 (PVSYST template 219, the original failure) and file 18
  (SREC template 78) both complete. NOTE: the historical alembic `ff04` `server_default` still reads
  `claude-sonnet-4-5`, but every insert path now sets `model_name` explicitly so it's never used.

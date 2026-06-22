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

## 2. Seeded prompt templates use a gateway-unsupported model
- Essentially every auto-seeded `extraction_prompt_templates` row declares
  `model_name = "claude-sonnet-4-5"`. The current Replit AI gateway rejects it with
  `UNSUPPORTED_MODEL`. This is **registry-wide**, not specific to any one document type.
- `gpt-5.2` is accepted by the gateway and is also `in_app_parsing_service.call_llm`'s default.
  `call_llm` only remaps `gpt-4*` (non-4.1) → `gpt-5.2`; a `claude-*` name passes through unchanged
  and then 400s.
- **Why:** so a "parse returns 400 UNSUPPORTED_MODEL" is an ops/config issue (seeded default vs
  gateway availability), not a prompt/schema bug.
- **How to apply:** for a one-off controlled validation run, force a supported model in the *script*
  (monkeypatch `call_llm` to pass `model_name="gpt-5.2"`) WITHOUT mutating the seeded registry — that
  still exercises the real prompt text, schema, and governed combine path. Changing the global default
  model touches every doc type and is out of scope for a single-doc-type sprint.

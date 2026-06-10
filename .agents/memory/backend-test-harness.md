---
name: backend test harness (ilios-server)
description: How to actually run the FastAPI backend pytest suite and the gotchas that make single-file runs fail.
---

# Running backend/ilios-server tests

- A **separate test database is required**: conftest builds its DSN from the
  `test_db_name` env var (read via dotenv). There is no committed `.env`, so the
  var is unset by default and the suite hangs/errors. Create a DB once
  (`createdb -h <host> <name>`) and run with `test_db_name=<name> pytest ...`.
- `pyproject.toml` `addopts` pins **full-app coverage** (`--cov=app
  --cov-fail-under=97`). Running a single file under that is slow and fails the
  coverage gate. Override per-run with `-o addopts="-q -p no:cacheprovider"`.
- **pytest-mock is NOT installed** in this environment — the `mocker` fixture
  does not exist even though many existing tests request it (those tests error
  on collection here). Use the built-in `monkeypatch` instead.
- Session setup itself (create_all + default roles + predefined data) is fast
  (~3-5s); a 2-min timeout earlier was coverage scanning the whole app, not setup.

# Auth gotchas in tests

- `PermissionType` (app/static/permissions.py) is a **plain class, not an enum** —
  `PermissionType.site`/`.company` ARE already the strings `"site"`/`"company"`, and
  it's used that way everywhere (`==` comparisons + dict keys). Never call `.value`
  on `permission_type` — it raises `AttributeError` on a str. (Contrast
  `AccessDecision`/`AccessDeniedReason` in access_resolver.py, which ARE real enums,
  so their `.value` calls there are correct.)
  Doing `.value` here used to 500 every **non-bypass (company-member) GET** through
  `get_authorized_site`/`get_authorized_company` (the access-decision logger runs on
  ALLOW *and* DENY), while platform-bypass/system users were unaffected (they return
  before logging). This is now FIXED — company-member auth headers work end-to-end;
  you no longer need `system_user_auth_header` just to dodge this crash.
- The shared `das_connection` fixture (tests/fixtures/connections.py) creates a
  connection via CRUD, which now **requires the provider be licensed to the
  company** (`CompanyDASProviderCRUD.has_provider`). Nothing assigns it, so the
  fixture 403s ("provider not assigned"). Assign it first with
  `CompanyDASProviderCRUD(db).assign_provider(company_id, provider)`.

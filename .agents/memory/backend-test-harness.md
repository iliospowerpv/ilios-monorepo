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

- `PermissionType` (app/static/permissions.py) is a **plain class, not an enum**.
  `project_access._log_access_decision` does `self.permission_type.value`, which
  raises `AttributeError: 'str' object has no attribute 'value'` on the ALLOW
  path. So any **company-member-authorized GET** through `get_authorized_site` /
  `get_authorized_company` crashes in that logging line.
  **Workaround in tests:** use `system_user_auth_header` — system users have
  `has_platform_bypass` and return before that logging runs.
- The shared `das_connection` fixture (tests/fixtures/connections.py) creates a
  connection via CRUD, which now **requires the provider be licensed to the
  company** (`CompanyDASProviderCRUD.has_provider`). Nothing assigns it, so the
  fixture 403s ("provider not assigned"). Assign it first with
  `CompanyDASProviderCRUD(db).assign_provider(company_id, provider)`.

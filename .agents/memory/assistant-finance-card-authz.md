---
name: Assistant finance card authorization
description: Finance action/navigator cards must mirror get_authorized_company, not just the Finance:view role permission.
---

# Finance action cards must authorize the company, not just the module

A finance read route enforces TWO independent gates, and a navigator/action card that deep-links to
it must reproduce BOTH or it leaks companies the caller cannot open:

1. `AuthorizedUser([FinancePermissions(view)])` — the Finance `view` *module* permission (a role flag).
2. `get_authorized_company(company_id, current_user, db_session)` — *entity* access to that specific
   company (effective-access resolver). Site finance additionally calls `get_authorized_site` and
   asserts `site.company_id == company_id`.

**Why:** the role flag is global; a user with Finance `view` does NOT thereby have access to *every*
company. Gating a `company_finance` / `site_finance` card on the role flag alone offered cards for
any `company_id` to any Finance-view user — a broken-access-control fail-closed violation.

**How to apply:**
- For `company_finance`: require Finance view AND `get_authorized_company(company_id)`.
- For `site_finance`: resolve a visible site, then pin the route's `company_id` to the site's OWN
  `company_id` (never a caller-supplied value — the route requires query company == site.company),
  then `get_authorized_company(site.company_id)`.
- `get_authorized_company` RAISES `HTTPException` on denial; in a card builder translate that to a
  boolean and fail closed (no card, no disclosure). Catch broad `Exception` → deny too.
- It's a FastAPI dependency but also a plain callable: `get_authorized_company(id, user, db)` works
  outside the request cycle. In tests, monkeypatch
  `app.helpers.authorization.project_access.get_authorized_company` (return a truthy entity to allow,
  raise `HTTPException` to deny).

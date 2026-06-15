---
name: Weather resolver W1 byte-identity + source tenant scoping
description: Why the DAS fallback must exclude historical-role profiles, and how weather sources are scoped to a site/company.
---

## DAS fallback must exclude role=historical profiles
The weather resolver's live-DAS fallback (`_resolve_das_window`) selects a
governing profile via `_select_active_profile(profiles, ...)`, which scans ALL
roles and derives both the active profile and `has_unapproved` (= profiles exist
but none active). W2 introduced `role=historical` profiles. If those are passed
into the DAS fallback, a *draft* historical profile flips `has_unapproved` true
(emitting the `weather_source_unapproved` indicator) and an *active-but-unusable*
one sets DAS `profile_id` — neither of which W1 would ever produce.

**Rule:** the DAS fallback must select its governing profile from
profiles with `role != historical` only. The historical path is chosen
separately (active role==historical that covers the window AND has physics-usable
observations); when it declines, DAS must behave exactly as if historical
profiles do not exist.

**Why:** the hard W2 invariant is "no active historical profile ⇒ live DAS path
byte-identical to W1." Cross-role profile selection silently violates it.

**How to apply:** when adding new profile roles or touching
`_select_active_profile` / `_resolve_das_window`, keep DAS provenance derived
only from the pre-W2 roles. Regression guards: resolver tests assert (a) draft
historical profile yields DAS provenance identical to the no-profile case, and
(b) active-unusable historical profile leaves DAS `profile_id is None`.

## Weather source tenant scoping
`WeatherSource` may be site-scoped, company-scoped, or global (both null).
`WeatherSourceCRUD.get_visible_to_site(site_id, source_id)` is the authorization
seam: visible iff site-scoped to that exact site, company-scoped to the site's
company, or global; any other site/company ⇒ None. Used by historical import
(`_resolve_source_id`), the create-profile router, and `create_historical_profile`
(defense-in-depth) so one tenant can never attach another's weather source.
**Why:** router site+company admin gating does not stop an authorized site-A
admin from passing site-B's `weather_source_id`.

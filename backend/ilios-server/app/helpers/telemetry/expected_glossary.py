"""Static glossary for the V2 "expected production" vocabulary.

This is the single source of truth for the human-readable definitions behind the
O&M / investor "expected" metadata contract. It is deliberately a plain,
in-process constant (no DB, no provider call) because the terms are part of the
product's domain language, not tenant data — every company sees the same text.

The frontend reads these via ``GET /api/operations-and-maintenance/glossary``
and renders them as info tooltips. Each term has a stable ``key`` so the FE can
look a definition up by key rather than by display string (display strings are
free to change for copy/i18n without breaking the lookup).

Suggested FE tooltip locations (where each ``key`` should surface), for the
implementer wiring the tooltips in a later frontend task:

* ``expected`` / ``actual`` / ``performance_index`` / ``actual_vs_expected`` /
  ``loss`` — the O&M site "Actual production" + "Actual vs Expected" cards
  (``SiteDashboardActualProductionSection``), the company actual-production card,
  and the investor companies table headers.
* ``expected_baseline`` / ``design_estimate`` — next to the baseline indicator on
  the site Telemetry / Expected baseline panel.
* ``state_available`` / ``state_partial`` / ``state_missing_inputs`` /
  ``state_pre_pto`` / ``state_baseline_not_available`` — the status chip/legend
  that renders the per-site or per-company ``expected_state``.
* ``na_vs_zero`` — the legend that explains why a metric shows "N/A" instead of 0.
* ``sites_with_telemetry`` / ``sites_with_active_baseline`` /
  ``sites_missing_baseline`` — the company/portfolio coverage caption shown when a
  company's expected is partial or unavailable.
* ``inverter_neutral`` — the inverter-performance tiles' status column header.

When the metadata contract changes (e.g. a new ``expected_state``), update this
module AND the corresponding schema/derivation so the glossary never drifts from
the values the API actually emits.
"""
from __future__ import annotations

# Category labels (kept as constants so the FE can group terms consistently).
CATEGORY_CORE = "Core metrics"
CATEGORY_BASELINE = "Baselines"
CATEGORY_STATE = "Expected status"
CATEGORY_COVERAGE = "Company coverage"
CATEGORY_DISPLAY = "Reading the values"
CATEGORY_WEATHER = "Weather provenance"

# Audience/scope tags: where a term is meaningful.
SCOPE_SITE = "site"
SCOPE_COMPANY = "company"
SCOPE_PORTFOLIO = "portfolio"
SCOPE_DEVICE = "device"

EXPECTED_GLOSSARY: list[dict] = [
    # ----- Core metrics ----------------------------------------------------
    {
        "key": "actual",
        "term": "Actual",
        "category": CATEGORY_CORE,
        "applies_to": [SCOPE_SITE, SCOPE_COMPANY, SCOPE_PORTFOLIO, SCOPE_DEVICE],
        "definition": (
            "Measured production read directly from the site's telemetry rollups. "
            "Power (kW) is the latest interval's average; cumulative actual (kWh) is "
            "today's energy so far, using the site's own local calendar day. A real "
            "0 (for example at night) is a true measured zero, not missing data."
        ),
    },
    {
        "key": "expected",
        "term": "Expected",
        "category": CATEGORY_CORE,
        "applies_to": [SCOPE_SITE, SCOPE_COMPANY, SCOPE_PORTFOLIO],
        "definition": (
            "Modeled production the system should have made under the measured "
            "weather, computed from the site's active baseline. Expected is only "
            "shown when it can be computed honestly; when inputs or a baseline are "
            "missing it is reported as N/A rather than guessed or set to 0."
        ),
    },
    {
        "key": "actual_vs_expected",
        "term": "Actual vs Expected",
        "category": CATEGORY_CORE,
        "applies_to": [SCOPE_SITE, SCOPE_COMPANY, SCOPE_PORTFOLIO],
        "definition": (
            "Actual divided by expected, as a percentage. It is only defined when "
            "both a real actual and a real, non-zero expected exist. If expected is "
            "N/A (or zero), the ratio is N/A, not 0%."
        ),
    },
    {
        "key": "performance_index",
        "term": "Performance index",
        "category": CATEGORY_CORE,
        "applies_to": [SCOPE_SITE],
        "definition": (
            "The actual-to-expected ratio expressed as a fraction (1.0 = met "
            "expectation). Like Actual vs Expected, it is N/A whenever expected is "
            "unavailable, so a missing baseline never looks like underperformance."
        ),
    },
    {
        "key": "loss",
        "term": "Loss",
        "category": CATEGORY_CORE,
        "applies_to": [SCOPE_COMPANY, SCOPE_PORTFOLIO],
        "definition": (
            "Expected energy minus actual energy, floored at 0 (production above "
            "expectation is reported as 0 loss, never negative). Loss is N/A when "
            "expected is N/A, because a shortfall cannot be measured without a "
            "trustworthy expected."
        ),
    },
    # ----- Baselines -------------------------------------------------------
    {
        "key": "expected_baseline",
        "term": "Expected baseline",
        "category": CATEGORY_BASELINE,
        "applies_to": [SCOPE_SITE, SCOPE_COMPANY],
        "definition": (
            "The active weather-adjusted model for a site that turns measured "
            "irradiance and cell temperature into expected production. Only an "
            "active weather-adjusted baseline drives the live expected values; a "
            "site with no active baseline shows expected as N/A."
        ),
    },
    {
        "key": "design_estimate",
        "term": "Design estimate",
        "category": CATEGORY_BASELINE,
        "applies_to": [SCOPE_SITE],
        "definition": (
            "A pre-construction or contractual production estimate. It is reference "
            "information only and does NOT drive the live expected shown on these "
            "charts — those come exclusively from the active weather-adjusted "
            "baseline."
        ),
    },
    # ----- Expected status (expected_state values) -------------------------
    {
        "key": "state_available",
        "term": "Available",
        "category": CATEGORY_STATE,
        "applies_to": [SCOPE_SITE, SCOPE_COMPANY, SCOPE_PORTFOLIO],
        "definition": (
            "Expected was computed in full for the period — every interval had the "
            "inputs it needed and a baseline was active. The expected and "
            "comparison values shown are complete and trustworthy."
        ),
    },
    {
        "key": "state_partial",
        "term": "Partial",
        "category": CATEGORY_STATE,
        "applies_to": [SCOPE_SITE, SCOPE_COMPANY, SCOPE_PORTFOLIO],
        "definition": (
            "Expected could be computed for some, but not all, of the period (or, "
            "for a company, some sites are not fully computable). To avoid a "
            "misleading partial total, the rolled-up expected is reported as N/A "
            "while the underlying actuals stay visible."
        ),
    },
    {
        "key": "state_missing_inputs",
        "term": "Missing inputs",
        "category": CATEGORY_STATE,
        "applies_to": [SCOPE_SITE],
        "definition": (
            "A baseline is active, but the weather inputs (irradiance / cell "
            "temperature) needed to compute expected were absent for the period, so "
            "expected is N/A. This is distinct from 'no baseline'."
        ),
    },
    {
        "key": "state_pre_pto",
        "term": "Pre-PTO",
        "category": CATEGORY_STATE,
        "applies_to": [SCOPE_SITE],
        "definition": (
            "The period predates the site's permission-to-operate / commissioning "
            "date, so no production is expected yet and expected is intentionally "
            "left as N/A rather than 0."
        ),
    },
    {
        "key": "state_baseline_not_available",
        "term": "Baseline not available",
        "category": CATEGORY_STATE,
        "applies_to": [SCOPE_SITE, SCOPE_COMPANY, SCOPE_PORTFOLIO],
        "definition": (
            "No active weather-adjusted baseline exists for the site (or for any "
            "telemetry-backed site in the company), so expected cannot be computed "
            "and is shown as N/A. Actual production is still displayed."
        ),
    },
    # ----- Company / portfolio coverage ------------------------------------
    {
        "key": "sites_with_telemetry",
        "term": "Sites with telemetry",
        "category": CATEGORY_COVERAGE,
        "applies_to": [SCOPE_COMPANY, SCOPE_PORTFOLIO],
        "definition": (
            "How many of the company's sites have native telemetry data feeding "
            "these charts. Sites without telemetry contribute nothing and do not "
            "count against expected coverage."
        ),
    },
    {
        "key": "sites_with_active_baseline",
        "term": "Sites with active baseline",
        "category": CATEGORY_COVERAGE,
        "applies_to": [SCOPE_COMPANY, SCOPE_PORTFOLIO],
        "definition": (
            "Of the telemetry-backed sites, how many have an active weather-adjusted "
            "baseline. A company's expected is only a complete number when every "
            "telemetry-backed site has one (and all compute fully)."
        ),
    },
    {
        "key": "sites_missing_baseline",
        "term": "Sites missing baseline",
        "category": CATEGORY_COVERAGE,
        "applies_to": [SCOPE_COMPANY, SCOPE_PORTFOLIO],
        "definition": (
            "Telemetry-backed sites that lack an active baseline. Any site here is "
            "why a company's expected may be reported as Partial or N/A instead of "
            "a single rolled-up figure."
        ),
    },
    # ----- Reading the values ----------------------------------------------
    {
        "key": "na_vs_zero",
        "term": "N/A vs 0",
        "category": CATEGORY_DISPLAY,
        "applies_to": [SCOPE_SITE, SCOPE_COMPANY, SCOPE_PORTFOLIO, SCOPE_DEVICE],
        "definition": (
            "N/A means a value could not be computed (missing baseline or inputs); "
            "0 means a real measured/derived zero. The platform never converts a "
            "missing value into 0, so the two are always distinguishable."
        ),
    },
    {
        "key": "inverter_neutral",
        "term": "Inverter status (neutral)",
        "category": CATEGORY_DISPLAY,
        "applies_to": [SCOPE_DEVICE],
        "definition": (
            "Inverter tiles show measured actual power but a neutral status with no "
            "per-inverter expected. Expected is modeled at the whole-plant level, "
            "and the platform does not split a site baseline down to individual "
            "inverters, so a per-device performance figure would be misleading."
        ),
    },
    # ----- Weather provenance (W1 resolver disclosure) ---------------------
    {
        "key": "weather_status_semantics_verified",
        "term": "Verified weather semantics",
        "category": CATEGORY_WEATHER,
        "applies_to": [SCOPE_SITE],
        "definition": (
            "The weather inputs driving expected are confirmed plane-of-array "
            "irradiance and cell (or module) temperature, because the site's "
            "telemetry streams are explicitly mapped to those measurements. This is "
            "the only case where the weather inputs are treated as fully trustworthy."
        ),
    },
    {
        "key": "weather_status_legacy_das_unverified",
        "term": "Unverified weather semantics",
        "category": CATEGORY_WEATHER,
        "applies_to": [SCOPE_SITE],
        "definition": (
            "Expected is computed from the existing DAS weather values, but those "
            "streams have not been mapped to a confirmed plane/temperature type. The "
            "numbers are used as-is to preserve current behavior; they are NOT "
            "assumed to be plane-of-array or cell temperature, and confidence is "
            "reported as unknown until the streams are mapped."
        ),
    },
    {
        "key": "weather_status_no_weather",
        "term": "No weather data",
        "category": CATEGORY_WEATHER,
        "applies_to": [SCOPE_SITE],
        "definition": (
            "Neither irradiance nor cell-temperature telemetry was present for the "
            "period, so no weather could be resolved and expected cannot be computed."
        ),
    },
    {
        "key": "missing_irradiance",
        "term": "Missing irradiance",
        "category": CATEGORY_WEATHER,
        "applies_to": [SCOPE_SITE],
        "definition": (
            "No irradiance telemetry was available for the period. Without "
            "irradiance the weather-adjusted expected cannot be computed, so it is "
            "reported as N/A rather than guessed."
        ),
    },
    {
        "key": "missing_cell_temperature",
        "term": "Missing cell temperature",
        "category": CATEGORY_WEATHER,
        "applies_to": [SCOPE_SITE],
        "definition": (
            "No cell-temperature telemetry was available for the period. The "
            "temperature correction cannot be applied, so expected is reported as "
            "N/A rather than guessed."
        ),
    },
    {
        "key": "semantics_unknown",
        "term": "Unknown weather semantics",
        "category": CATEGORY_WEATHER,
        "applies_to": [SCOPE_SITE],
        "definition": (
            "The site's weather streams are not yet mapped to a confirmed "
            "irradiance plane and temperature type. The platform never assumes an "
            "unmapped irradiance stream is plane-of-array or that a temperature is "
            "cell temperature; map the streams to upgrade to verified semantics."
        ),
    },
    {
        "key": "why_unverified",
        "term": "Why this is unverified",
        "category": CATEGORY_WEATHER,
        "applies_to": [SCOPE_SITE],
        "definition": (
            "Expected used existing DAS weather whose measurement semantics are not "
            "confirmed. The values are passed through unchanged (no transposition or "
            "ambient-to-cell conversion is performed), but they are labelled "
            "unverified so the disclosure stays honest."
        ),
    },
    {
        "key": "confidence_unknown",
        "term": "Confidence unknown",
        "category": CATEGORY_WEATHER,
        "applies_to": [SCOPE_SITE],
        "definition": (
            "No confidence band could be established for the weather inputs, "
            "typically because the stream is unmapped or its source has no declared "
            "confidence. Confidence is left as unknown rather than assumed."
        ),
    },
    {
        "key": "profile_missing",
        "term": "No weather policy",
        "category": CATEGORY_WEATHER,
        "applies_to": [SCOPE_SITE],
        "definition": (
            "No active weather source policy (profile) governs this site for the "
            "period. Expected still uses the available DAS weather, but no approved "
            "policy yet declares which source should drive weather."
        ),
    },
    {
        "key": "weather_source_unapproved",
        "term": "Weather policy not approved",
        "category": CATEGORY_WEATHER,
        "applies_to": [SCOPE_SITE],
        "definition": (
            "A weather source policy exists for the site but has not been approved "
            "into an active state, so it does not yet govern weather resolution."
        ),
    },
    {
        "key": "below_confidence_threshold",
        "term": "Below confidence threshold",
        "category": CATEGORY_WEATHER,
        "applies_to": [SCOPE_SITE],
        "definition": (
            "The resolved weather confidence is lower than the minimum the active "
            "policy requires. The value is still shown, but flagged so reviewers "
            "know it does not meet the configured confidence floor."
        ),
    },
    {
        "key": "modeled_not_available",
        "term": "Modeled weather not used",
        "category": CATEGORY_WEATHER,
        "applies_to": [SCOPE_SITE],
        "definition": (
            "The active policy permits modeled-weather fallback, but the platform "
            "resolves measured DAS weather only at this stage and never silently "
            "substitutes a modeled value."
        ),
    },
]

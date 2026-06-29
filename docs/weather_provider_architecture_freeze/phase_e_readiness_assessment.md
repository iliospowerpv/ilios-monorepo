# Phase E Readiness Assessment — Weather Provider Framework

> **Architecture freeze (D.6). Documentation only — this does NOT authorize Phase E.**
> Phase E is the hypothetical future work that would let external weather participate
> in **physics** (expected energy / baselines) — i.e. crossing the line that ADR-0001,
> ADR-0002, and ADR-0004 deliberately hold. This document states what Phase E would
> have to satisfy **before** it may be reviewed, so the freeze remains a clean
> baseline.

## 0. The boundary Phase E proposes to cross

Today, external **provider** weather (Open-Meteo-style `ghi`/`ambient` pulls) is
**context-only**. The resolver already consumes *measured/approved* POA/cell — DAS
streams (W1) and approved historical profiles (W2) — but it has **no path that derives**
POA from GHI/DNI/DHI or cell from ambient. Phase E is exactly that missing derivation:
for the first time it would let an external GHI/ambient observation become a
**physics-usable** POA/cell quantity that could change
`compute_site_expected_period_effective`. That transposition/thermal modeling is a
fundamentally different risk class (accuracy + liability) and **must be reviewed
separately**, not folded into provider/governance work.

> **Gate statement:** No part of Phase E may begin in the same change set that frees
> the architecture. Phase E requires its own design, its own review, and explicit
> sign-off against the criteria below.

## 1. Remaining prerequisites (technical)

- [ ] **A transposition model** (GHI/DNI/DHI → POA) chosen and specified (e.g. isotropic
      vs Perez), including required inputs (solar position, tilt, azimuth, albedo) and
      their provenance.
- [ ] **A cell-temperature model** (ambient + irradiance + wind → cell) chosen and
      specified (e.g. NOCT / Sandia), including required module thermal parameters.
- [ ] **Per-site geometry & module parameters** available and governed (tilt, azimuth,
      module thermal coefficients) — currently not guaranteed present for external-only
      sites.
- [ ] **A new, explicit resolver path** (ADR-0002 says the current resolver is frozen):
      Phase E adds a *separate, reviewed* selection/derivation path; it does not mutate
      the existing one in place.
- [ ] **Semantics promotion path** with proof: only governed, validated declarations
      may move `unknown → poa/cell`, and only via modeled derivation that is labeled as
      modeled (not measured).
- [ ] **Backward-compatibility proof:** with Phase E disabled, expected math remains
      byte-identical to the frozen baseline.

## 2. Risks (and why the freeze mitigates them)

| Risk | Impact | Mitigation owed by Phase E |
|---|---|---|
| Silent GHI→POA mislabeling | Wrong expected energy, eroded trust | Modeled values labeled modeled; never written as measured `poa`. |
| Ambient treated as cell | Overstated expected in heat | Explicit cell model; validation vs measured cell where available. |
| Model accuracy varies by site/climate | Misleading confidence | Per-site/seasonal validation + confidence reporting (ADR-0001's `confidence` field). |
| Scope creep into the frozen resolver | Loss of the single audit gate | Separate reviewed path; resolver diff in a provider PR stays blocking. |
| Liability of provider-derived physics | Contractual/reporting exposure | Product/legal sign-off + provider licensing review for physics use. |

## 3. Scientific validation requirements

Phase E must not ship a model on assertion alone. Required:
- [ ] **Ground-truth comparison:** modeled POA/cell vs co-located measured POA/cell
      (governed sources) across multiple sites, seasons, and sky conditions.
- [ ] **Error characterization:** report bias and dispersion (e.g. MBE/RMSE) per site
      and per regime; define acceptance thresholds **before** testing.
- [ ] **Confidence semantics:** map validation results onto the existing `confidence`
      enum so downstream consumers can see modeled-input confidence.
- [ ] **Failure honesty:** when inputs are insufficient for the model, expected stays
      **null** (never `0`, never a low-confidence guess presented as fact).
- [ ] **Independent review** of the model choice and validation methodology.

## 4. Data requirements

- [ ] Sufficient external coverage + the **right variables** (GHI and/or DNI/DHI, plus
      ambient, ideally wind) — many free providers give GHI+ambient only, which bounds
      model choice.
- [ ] Governed **per-site geometry/module** parameters (tilt, azimuth, thermal coeffs).
- [ ] Co-located **measured** POA/cell for validation (at least on a representative
      validation set).
- [ ] Provenance and `confidence` populated end-to-end so modeled inputs are
      distinguishable from measured.
- [ ] Solar-position computation inputs (lat/long/elevation/timezone) — note the
      per-site IANA timezone already exists and is used for site-local day boundaries.

## 5. Governance checkpoints (must all pass before Phase E review concludes)

1. [ ] **Architecture freeze acknowledged:** this package (D.6) is the baseline; any
       Phase E design references it and lists exactly which ADRs it intends to revise
       (expected: ADR-0001, -0002, -0004) and why.
2. [ ] **Separate review:** Phase E is reviewed on its own, with scientific +
       product/legal reviewers, not bundled with provider/ops work.
3. [ ] **Provider licensing for physics use** re-examined (context-use licensing ≠
       physics/derived-product licensing).
4. [ ] **Rollback story:** Phase E ships behind a flag; disabling it restores
       byte-identical expected math.
5. [ ] **No-regression proof:** the D.6 golden tests (resolver immutability, expected
       byte-identity, context-only, GHI≠POA) still pass with Phase E **off**.
6. [ ] **Operational readiness:** runbooks/DR updated for modeled inputs; integrity
       checks extended to flag improperly promoted semantics.

## 6. Readiness verdict (as of the freeze)

| Dimension | Status |
|---|---|
| Architecture frozen & documented | ✅ This package |
| Context-only data plane in place | ✅ Built (A–D) |
| Governance/ops design | ✅ Designed (D.5); ⏳ build (D.5a) |
| Transposition / cell model chosen | ❌ Not started (Phase E) |
| Per-site geometry/module params governed | ❌ Not guaranteed (Phase E) |
| Scientific validation framework | ❌ Not started (Phase E) |
| Physics-use licensing/legal sign-off | ❌ Not started (Phase E) |

**Conclusion.** The architecture is **ready to be frozen** and is in a clean state to
*prepare* for Phase E. Phase E itself is **not ready to begin** and must clear the
prerequisites, scientific validation, data, and governance checkpoints above under a
**separate** review. Until then, every frozen invariant in `adrs.md` remains in force.

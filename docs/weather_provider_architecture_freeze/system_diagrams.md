# System Diagrams — Weather Provider Framework (Architecture Freeze)

> **Planning/documentation only.** Diagrams are Mermaid (render in markdown).
> Build tags: **[BUILT]** Phases A–D, **[DESIGNED]** D.5, **[FUTURE]** Phase E.
> The single most important diagram is **§4 Resolver Boundaries** — it shows the
> structural line that keeps external weather context-only.

---

## 1. Provider lifecycle (catalog) — [DESIGNED, D.5a]

Catalog entries are **global** and start disabled + unapproved. Enabling requires
approval. Disable/suspend/retire never delete data. Rollback of a transition is a new
reverse transition recorded in the append-only audit ledger.

```mermaid
stateDiagram-v2
    [*] --> draft: seeded (is_enabled=false)
    draft --> approved: approve (platform-admin)
    approved --> enabled: enable (requires approved)
    enabled --> disabled: safe disable (data retained)
    disabled --> enabled: re-enable
    enabled --> suspended: suspend (force-disable)
    disabled --> suspended: suspend
    suspended --> approved: clear suspension
    approved --> retired: retire
    enabled --> retired: retire (force-disable)
    disabled --> retired: retire
    suspended --> retired: retire
    retired --> approved: restore
    note right of enabled
        Only enabled + approved providers
        can be pulled. Company entitlement
        further scopes WHICH companies.
    end note
```

---

## 2. Import lifecycle (job) — [DESIGNED, D.5a]

Jobs run **synchronously** (no scheduler). Triggers are manual / retry / re_preview
only. A job references the immutable batch it produced.

```mermaid
stateDiagram-v2
    [*] --> queued: operator action
    queued --> running: claim site/provider lock
    running --> succeeded: all rows written / already present
    running --> partial: some rows / some errors
    running --> failed: provider or credential error
    succeeded --> [*]
    partial --> [*]
    failed --> [*]
    note right of running
        Idempotency: a partial-unique index on
        idempotency_key for queued/running jobs
        rejects a duplicate concurrent pull.
        retry creates a NEW job (parent_job_id set).
    end note
```

---

## 3. Provenance flow — [BUILT] with [DESIGNED] job overlay

How a pull becomes auditable context. Note the terminal split: data lands in the
**context plane**, never the **physics plane**.

```mermaid
flowchart TD
    OP["Operator triggers import (manual)"] --> CTX{"_resolve_provider_pull_context"}
    CTX -->|catalog enabled?| G1["Catalog gate: is_enabled [BUILT] (+approved/entitlement [DESIGNED])"]
    CTX -->|licensing| G2["Default-deny licensing gate [BUILT]"]
    CTX -->|credentials| G3["Durability gate, prod-like only [BUILT]"]
    G1 --> ADAPT["Provider adapter pull (bounded window)"]
    G2 --> ADAPT
    G3 --> ADAPT
    ADAPT --> JOB["weather_provider_import_job [DESIGNED]"]
    JOB --> BATCH["weather_observation_batches (immutable) [BUILT]"]
    BATCH --> OBS["weather_observations: dedupe_key, ON CONFLICT DO NOTHING [BUILT]"]
    OBS --> SEM{"declared semantics"}
    SEM -->|"ghi / ambient / unknown"| CONTEXT["CONTEXT PLANE: external-weather-context, dashboards, readiness signals"]
    SEM -.->|"poa / cell ONLY via governed declaration"| PHYS["PHYSICS PLANE (resolver) — NOT reachable from external GHI"]
    CONTEXT --> AUDIT["Audit + integrity reporting"]
    style PHYS fill:#fdd,stroke:#900,stroke-width:2px
    style CONTEXT fill:#dfd,stroke:#090
```

---

## 4. Resolver boundaries (THE freeze) — [BUILT]

The hard line. External `provider_pull` observations (`ghi/ambient/unknown`) are
visible to context surfaces but are **not selectable** by `WeatherResolver`: it selects
only governed POA/cell sources — DAS streams (W1) or an approved POA/cell historical
profile (W2) — and applies a POA-only / cell-only acceptance test that GHI/ambient data
cannot pass. (The resolver is not blind to all of `weather_observations`; it is blind to
*provider GHI/ambient* data specifically.)

```mermaid
flowchart LR
    subgraph CONTEXT["Context plane (external weather) [BUILT]"]
        EXT["External provider observations<br/>ghi / ambient / unknown"]
        CCTX["external-weather-context<br/>physics_usable_rows = 0"]
        EXT --> CCTX
    end

    subgraph PHYSICS["Physics plane (expected/baseline) [BUILT, FROZEN]"]
        WR["WeatherResolver.resolve_window"]
        TEST{"POA-only / cell-only<br/>acceptance test"}
        EXP["compute_expected_buckets"]
        EFF["compute_site_expected_period_effective"]
        WR --> TEST -->|accept POA+cell| EXP --> EFF
        TEST -->|reject otherwise| NULL["expected = null (never 0)"]
    end

    EXT -. "excluded: ghi/ambient/unknown<br/>fails POA/cell test (ADR-0004)" .-> WR
    GOV["Governed POA/cell source<br/>DAS (W1) or approved historical profile (W2)"] --> WR

    style EXT fill:#dfd,stroke:#090
    style WR fill:#fdd,stroke:#900,stroke-width:2px
    style PHYSICS fill:#fff5f5
```

---

## 5. Operational governance — [BUILT gates] + [DESIGNED lifecycle/audit]

The control plane around the data plane: authorization scope, the three gates, and
the append-only audit trail.

```mermaid
flowchart TD
    subgraph AUTHZ["Authorization"]
        PA["Platform-admin → catalog lifecycle (global)"]
        TA["telemetry_admin + company visibility → accounts, import"]
        AV["asset-view + company visibility → read context/metrics"]
    end

    subgraph GATES["Gates"]
        L["Default-deny licensing, ack required [BUILT]"]
        D["Durability gate, prod-like envs [BUILT]"]
        C["Catalog gate: is_enabled [BUILT];<br/>approved + entitlement [DESIGNED]"]
    end

    subgraph AUDIT["Audit / observability"]
        CAUD["weather_provider_catalog_audit (append-only) [DESIGNED]"]
        SAUD["weather_source_approvals (append-only) [BUILT]"]
        LOGS["Structured event logs [DESIGNED]"]
        MET["Read-only metrics / health endpoints [DESIGNED]"]
    end

    PA --> C
    TA --> L --> D --> C
    C --> RUN["Import allowed"]
    RUN --> CAUD
    RUN --> LOGS
    RUN --> MET
    PA --> CAUD
    AV --> MET
```

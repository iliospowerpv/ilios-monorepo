# iliOS - REA Investment Platform

## Overview
iliOS is a real estate asset investment management platform designed to manage the entire lifecycle of real estate investments, from acquisition and due diligence to asset management, financial tracking, and reporting. The platform aims to enhance decision-making through data-driven insights and improve operational efficiency for real estate investors and asset managers. iliOS provides secure user authentication, multi-company user membership, a user-centric workspace, comprehensive asset and task management, financial oversight with budgeting and vendor management, sales pipeline tracking, and robust reporting tools. It serves as a centralized system for investment oversight and operational governance for real estate professionals, with a vision to become the leading platform for data-driven real estate investment.

## User Preferences
I prefer detailed explanations and thorough documentation for any implemented features or architectural decisions.
I expect iterative development, with clear communication before significant changes are made.
Do not change the fundamental "Site" entity in the backend; use "Project" only as a UI terminology update.

## System Architecture

### Frontend
- **Technology Stack**: React 18, TypeScript, Material UI (MUI), React Query, React Router DOM, AG Grid, Chart.js, Webpack 5.
- **UI/UX Decisions**: Standardized "Projects" terminology, robust navigation (Entity Context, Module Sidebar, Breadcrumb), a unified Context Bar for scope management, a static Asset Management Overview with drag-and-drop features, a collapsible sidebar, and consolidated admin/settings modules. Unified company landing page at `/project-hub/companies/:companyId` with Overview, Projects, Tasks, and Performance tabs.
- **Data Room**: Hybrid PDF/document viewer with AI-extracted field linking, programmatic navigation, text search, highlighting, audit trail, and a sequential verification workflow with bulk acceptance. Features a collapsible Project Summary Panel for cross-document analysis.

### Backend
- **Technology Stack**: Python 3.11, FastAPI, SQLAlchemy, Alembic, PostgreSQL.
- **Core Modules**: Workspace, Finance (capital governance, budgeting, vendor management), Acquisitions (13-stage deal pipeline), and Project Hub (unified asset management and due diligence).
- **Access Control**: Multi-Company Access System with granular authorization using a Canonical Effective-Access Resolver and Module-Level Permission Enforcement. Includes a Role Profiles System and a Portfolio Hub Boundary Model for data visibility.
- **Telemetry Module**: Project-scoped and company-scoped telemetry for Data Acquisition Systems (DAS) integration, health monitoring, and device mapping. Features a V2 architecture with a DB-backed provider catalog, pluggable `ProviderAdapter` abstraction, durable credential storage using GCP Secret Manager, and a three-state account model. Includes a demo telemetry system for simulated solar data.
- **Native Telemetry Ingestion (V2)**: In-platform readings ingestion that replaces the legacy GCP/BigQuery/Firestore pull. Persists raw device/site readings and interval rollups directly in PostgreSQL (no BigQuery, Firestore, or Cloud Functions; GCP Secret Manager is still used only for provider credentials). A DB-driven metric catalog (`TelemetryMetricCatalog`) maps provider fields to normalized metrics/units, and a `ReadingsAdapter` capability on the provider adapter pulls readings over a bounded window. The `run_site_refresh` ingestion service resolves the site mapping, provider account, catalog, and mapped devices, then writes via fully idempotent chunked upserts (deduped on a null-safe `dedupe_key`); it never deletes or wipes existing data, and provider/credential failures are recorded on the sync job without touching readings. A separate `run_rollups_for_window` rollup service computes epoch-anchored interval aggregates (15m/30m/1h/1d, avg) for site and device levels in an isolated transaction so a rollup failure can never undo committed readings. Every ingestion attempt is tracked as a `TelemetrySyncJob` (queued/running/succeeded/partial/failed).
- **Automatic Telemetry Scheduler**: Scheduled ingestion is handled by an in-process daemon scheduler (`TelemetrySchedulerRunner`, started from the FastAPI `lifespan`) that polls `telemetry_scheduler_state` every 60s for due sites, claims each via an atomic DB lease (so at most one run executes per site across `--reload` restarts/workers), and runs the same ingestion + bucket-aligned rollup pipeline as the manual refresh with `trigger=scheduled`. The cursor (`last_successful_pull_at`) advances only when both readings upsert and rollup succeed, so failures resume the same gap with idempotent overlap. The runner is gated behind the opt-in `telemetry_scheduler_enabled` flag AND `telemetry_v2_enabled` AND (in production-like environments) a durable credential store; when any gate fails it logs the reason at startup and never starts. Note: settings use `case_sensitive=True`, so the env var key must be lowercase (`telemetry_scheduler_enabled`).
- **Manual "Refresh Telemetry"**: User-facing manual ingestion trigger on a single mapped project/site. Backend `POST /api/telemetry/v2/sites/{site_id}/refresh-readings` (telemetry-admin + company-visibility enforced; blocked when storage is non-durable in production) accepts an optional window (defaults to the most recent 24h, clamped to a 24h max), runs the ingestion + rollup pipeline, writes a best-effort audit log, and returns a structured summary for every outcome. The frontend exposes a reusable `RefreshTelemetryButton` in the project Telemetry tab (shown once telemetry is configured) with progress, success/partial/failure feedback, and a last-refreshed indicator; on success it refreshes the site's readiness and health panels.
- **Document Versioning & Promotion**: Manages lender-quality Data Room document versions with a "Promote to Current Assumptions" workflow, supporting `candidate`, `active`, and `retired` `ProjectFact` states.
- **Poison Pill Toggle**: Interactive flag on due diligence document keys allowing users to manually mark terms as poison pills, persisted via `is_poison_pill` and `poison_pill_notes`. User-set flags take precedence over AI-detected flags.
- **Extraction Registry & Prompt Studio**: Scalable system for dynamic document type and field configuration using database-driven schemas and prompt templates.
- **In-App AI Parsing**: Fully in-app document parsing using Replit AI Integrations (OpenAI), featuring an `InAppParsingService` for file handling, text extraction, LLM calls, observability, and retry logic. Implements idempotency and concurrency safety.
- **Storage Service Abstraction**: Replit-native storage architecture with an abstract `StorageService` interface, supporting `ReplitStorageService`, optional `GCSStorageService`, and `HybridStorageService`.
- **Data Room Acceptance Safety**: Enforces parse run history panel for files and validates `run_id` and run status before allowing bulk acceptance of extracted data.
- **Contacts System**: CRM-style contact management for tracking external people related to portfolio, company, and project entities.
- **Finance Integration & Data Ingestion**: Company-level, read-only integration supporting multiple external providers with a pluggable architecture. Encrypted credentials, role-based access, and normalized storage with upsert semantics.
- **Company & Site Creation**: Restricted company creation with structured address fields. Site creation requires `assets_management:edit` permission.
- **Per-Site Timezone**: Each Site stores an additive IANA `timezone` column (NOT NULL, server default `UTC`), set explicitly via the Site form (no auto-derivation from state). App-wide timestamps still render in the viewer's browser timezone; the site timezone is used ONLY for site-local telemetry computations — specifically the daily/"today" production boundary — by converting the site's local midnight to a naive-UTC instant for rollup queries (UTC fallback + warning on missing/invalid values, since readings/rollups are stored naive-UTC). A general `PUT /api/sites/{site_id}` endpoint (`assets_management:edit`, full-replace semantics, tolerates but ignores `company_id` so a site is never re-parented) persists site edits including the timezone.
- **Entity Directory System**: Portfolio-scoped directory of legal/business entities with project-level and deal-level role assignments, including a dedicated Portfolio Admin page and a shared `EntityPicker` UI component.
- **Project Import Tool**: Bulk import projects from CSV/XLSX files via a multi-step wizard (Upload → Map Fields → Validate → Import) with auto-mapping, validation, and duplicate detection.
- **Archive & Restore (Soft-Delete)**: Companies and Projects/Sites support soft-delete via `is_archived` flags with cascade archiving.
- **Home Dashboard "Your Projects" Widget**: Extends `/api/workspace` with project data for displaying access-controlled project cards.
- **In-App Performance Report**: Fallback reporting for demo sites where PowerBI has no BigQuery data, generating daily/monthly performance data using the demo telemetry pipeline.

## External Dependencies
- **PostgreSQL**: Primary relational database.
- **Redis**: Used for caching and session management.
- **PowerBI**: Integrated for reporting and business intelligence.
- **Mailgun**: Configured for email services.
- **Rombus**: Integrated for camera/security functionalities.
- **AG Grid**: Enterprise license for advanced table functionalities.
- **OpenAI**: Utilized for in-app AI parsing capabilities.
- 
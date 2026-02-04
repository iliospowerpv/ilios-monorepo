# iliOS - REA Investment Platform

## Overview
iliOS is a real estate asset investment management platform designed to manage the entire lifecycle of real estate investments, from acquisition and due diligence to asset management, financial tracking, and reporting. The platform aims to enhance decision-making through data-driven insights and improve operational efficiency for real estate investors and asset managers. Key capabilities include secure user authentication, multi-company user membership, a user-centric workspace, comprehensive asset and task management, financial oversight with budgeting and vendor management, sales pipeline tracking, and robust reporting tools. iliOS serves as a centralized system for investment oversight and operational governance for real estate professionals.

## User Preferences
I prefer detailed explanations and thorough documentation for any implemented features or architectural decisions.
I expect iterative development, with clear communication before significant changes are made.
Do not change the fundamental "Site" entity in the backend; use "Project" only as a UI terminology update.

## System Architecture

### Frontend
- **Technology Stack**: React 18, TypeScript, Material UI (MUI), React Query, React Router DOM, AG Grid, Chart.js, Webpack 5.
- **UI/UX Decisions**: Standardized "Projects" terminology, robust navigation (Entity Context, Module Sidebar, Breadcrumb), a unified Context Bar for scope management, a static Asset Management Overview with drag-and-drop features, a collapsible sidebar, and consolidated admin/settings modules for improved user experience and access control.

### Backend
- **Technology Stack**: Python 3.11, FastAPI, SQLAlchemy, Alembic, PostgreSQL.
- **Core Modules**: Workspace, Finance (capital governance, budgeting, vendor management), Acquisitions (13-stage deal pipeline), and Project Hub (unified asset management and due diligence).
- **Access Control**: Multi-Company Access System, Canonical Effective-Access Resolver for granular authorization (fail-closed, restrict-only semantics), and Module-Level Permission Enforcement with `permission_guards.py`.
- **Diligence Module**: Migrated to canonical permission guards for all endpoints.
- **Role Profiles System**: Granular stakeholder role definitions augmenting base roles.
- **Portfolio Hub Boundary Model**: Links companies within a hub for controlled data visibility.
- **Architectural Guardrails**: Asset Management Overview is a static record, linking to operational modules for live metrics.
- **Telemetry Module**: Project-scoped telemetry for Data Acquisition Systems (DAS) integration, health monitoring, and device mapping CRUD with Firestore sync.
- **Document Versioning & Promotion System**: Implements lender-quality Data Room document versioning with "Promote to Current Assumptions" workflow, managing `candidate`, `active`, and `retired` `ProjectFact` states with atomic transactions and diff computation.
- **Extraction Registry & Prompt Studio**: Scalable system for dynamic document type and field configuration using database-driven schemas, prompt templates, and an `ExtractionPipelineService` with registry-first lookup. Supports re-extraction workflows with binding snapshots for auditability. Includes an Admin API and UI for management.
- **In-App AI Parsing (Replit-Native)**: Fully in-app document parsing using Replit AI Integrations (OpenAI), removing external cloud function dependencies. Features `InAppParsingService` for file handling, text extraction (PDF, DOCX), LLM calls via FastAPI BackgroundTasks, observability with correlation IDs, and retry logic with exponential backoff.
    - **Phase 2A Idempotency & Concurrency Safety**: Prevents duplicate parsing and race conditions:
        - New `queued` status. Jobs created as `queued`, then atomically claimed to `processing`.
        - Partial unique index `ix_ai_parsing_results_active_unique` on (file_id, COALESCE(document_type_id, -1), COALESCE(schema_version_id, -1), COALESCE(prompt_template_id, -1)) WHERE status IN ('queued', 'processing') enforces idempotency at DB level.
        - `create_or_get_active()` uses IntegrityError handling for concurrent request safety.
        - `atomic_claim()` uses `SELECT ... FOR UPDATE` row locking for background task safety.
        - Claim columns: `worker_id`, `correlation_id`, `claimed_at`.
        - Terminal state guarantees: `mark_completed()` and `mark_failed()` always set `end_time`.
- **Storage Service Abstraction**: Replit-native storage architecture with an abstract `StorageService` interface, `ReplitStorageService` (default), optional `GCSStorageService`, and `HybridStorageService` for migration support. Utilizes new direct upload and download endpoints.

## External Dependencies
- **PostgreSQL**: Primary relational database.
- **Redis**: Used for caching and session management.
- **PowerBI**: Integrated for reporting and business intelligence.
- **Mailgun**: Configured for email services.
- **Rombus**: Integrated for camera/security functionalities.
- **AG Grid**: Enterprise license for advanced table functionalities.
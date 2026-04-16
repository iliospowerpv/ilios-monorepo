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
- **UI/UX Decisions**: Standardized "Projects" terminology, robust navigation (Entity Context, Module Sidebar, Breadcrumb), a unified Context Bar for scope management, a static Asset Management Overview with drag-and-drop features, a collapsible sidebar, and consolidated admin/settings modules for improved user experience and access control. Unified company landing page at `/project-hub/companies/:companyId` with Overview (company info, portfolio summary, module Quick Actions), Projects, Tasks, and Performance tabs; legacy `/companies/:companyId` redirects there. The Performance tab surfaces portfolio-level O&M charts (Actual vs Expected bubble chart and Daily Losses bar chart) by reusing existing O&M widgets, with a clean empty state for companies without telemetry data.
- **Data Room**: Hybrid PDF/document viewer with AI-extracted field linking, programmatic navigation, text search, highlighting, and an audit trail with a sequential verification workflow and bulk acceptance. Features a collapsible Project Summary Panel for cross-document analysis.

### Backend
- **Technology Stack**: Python 3.11, FastAPI, SQLAlchemy, Alembic, PostgreSQL.
- **Core Modules**: Workspace, Finance (capital governance, budgeting, vendor management), Acquisitions (13-stage deal pipeline), and Project Hub (unified asset management and due diligence).
- **Access Control**: Multi-Company Access System with granular authorization using a Canonical Effective-Access Resolver and Module-Level Permission Enforcement. Includes a Role Profiles System and a Portfolio Hub Boundary Model for data visibility.
- **Architectural Guardrails**: Asset Management Overview functions as a static record, linking to operational modules for live metrics.
- **Telemetry Module**: Project-scoped telemetry for Data Acquisition Systems (DAS) integration, health monitoring, and device mapping. Supports company-scoped DAS providers. Includes a **Demo Telemetry System** with database-driven `is_demo` flag on companies, toggled via `DEMO_TELEMETRY=true` env var. Demo companies' sites receive realistic simulated solar data (bell-curve production, seasonality, weather variability, degradation) with injected demo events (inverter outage, clipping, severe weather, intermittent faults). Data flows through the same pipeline as live telemetry (intercepted at `BaseTelemetryBigQuery` level). Non-demo companies are completely unaffected. Demo telemetry infrastructure (DAS connection, site mappings, device mappings) is seeded via `scripts/seed_demo_telemetry.py` (seed/cleanup). Device power uses DB-derived inverter count per site for correct capacity scaling.
- **Document Versioning & Promotion**: Manages lender-quality Data Room document versions with a "Promote to Current Assumptions" workflow, supporting `candidate`, `active`, and `retired` `ProjectFact` states.
- **Poison Pill Toggle**: Interactive flag on due diligence document keys allowing users to manually mark terms as poison pills. Persisted via `is_poison_pill` and `poison_pill_notes` columns on `document_keys`. PATCH endpoint at `/{document_id}/keys/{key_id}/poison-pill` supports upsert (key_id=0 with key_name). User-set flags take precedence over AI-detected flags in data merge.
- **Extraction Registry & Prompt Studio**: Scalable system for dynamic document type and field configuration using database-driven schemas and prompt templates.
- **In-App AI Parsing**: Fully in-app document parsing using Replit AI Integrations (OpenAI), featuring an `InAppParsingService` for file handling, text extraction, LLM calls via FastAPI BackgroundTasks, observability, and retry logic. Implements idempotency and concurrency safety.
- **Storage Service Abstraction**: Replit-native storage architecture with an abstract `StorageService` interface, supporting `ReplitStorageService`, optional `GCSStorageService`, and `HybridStorageService`.
- **Data Room Acceptance Safety**: Enforces parse run history panel for files and validates `run_id` and run status before allowing bulk acceptance of extracted data.
- **Contacts System**: A CRM-style contact management system for tracking external people related to portfolio, company, and project entities, stored at three levels with exact-scope filtering.
- **Finance Integration & Data Ingestion**: Company-level, read-only integration supporting multiple external providers with a pluggable architecture. Encrypted credentials, role-based access, and normalized storage (`finance_accounts`, `finance_transactions`, `finance_sync_runs` tables) with upsert semantics. Includes company-level finance health indicators.
- **Company & Site Creation**: Restricted company creation with structured address fields. Site creation requires `assets_management:edit` permission.
- **Entity Directory System**: Portfolio-scoped directory of legal/business entities with project-level and deal-level role assignments, including a dedicated Portfolio Admin page for centralized management and a shared `EntityPicker` UI component.
- **Project Import Tool**: Bulk import projects from CSV/XLSX files via a multi-step wizard (Upload → Map Fields → Validate → Import) with auto-mapping, validation, duplicate detection, and full project initialization.
- **Archive & Restore (Soft-Delete)**: Companies and Projects/Sites support soft-delete via `is_archived` flags with cascade archiving for companies. Admin-only PATCH endpoints for archive/restore and filterable lists.
- **Home Dashboard "Your Projects" Widget**: Extends `/api/workspace` with project data for displaying access-controlled project cards on the Home Dashboard.
- **In-App Performance Report**: Fallback reporting for demo sites where PowerBI has no BigQuery data. Backend endpoint (`/api/reporting/sites/{site_id}/performance-report/`) generates daily/monthly performance data using the demo telemetry pipeline. Frontend `InAppPerformanceReport` component renders KPI cards and AG Charts (daily generation, performance ratio, monthly breakdown). Activates only when: (1) the selected report type is "Performance Report", (2) the site is a demo site with `DEMO_TELEMETRY=true`. Non-demo sites and non-performance report types continue to use PowerBI embedding normally. Includes site-level access control enforcement and input validation.

## Documentation Governance
- **Mandatory Rule**: All features must have corresponding documentation before being considered complete.
- **Route-Help Registry**: `docs/route-help-registry.json` maps every app route to its help article slugs.
- **Coverage Inventory**: `docs/documentation-coverage.json` tracks documentation status per module/page.
- **Audit Script**: Run `npm run docs:audit` from `frontend/rea-investment-fe` to check coverage gaps.
- **Developer Guide**: `docs/DOCUMENTATION_REQUIREMENTS.md` contains the full checklist and how-to instructions.
- **AI Guardrails**: `docs/AI_DEVELOPMENT_GUARDRAILS.md` instructs AI agents to update docs with every feature change.
- Any new module, page, workflow, report, dashboard, field, metric, status, navigation item, setting, permission, integration, or data concept requires: help content, FAQ updates, glossary entries, route-to-help mappings, and contextual help links.

## External Dependencies
- **PostgreSQL**: Primary relational database.
- **Redis**: Used for caching and session management.
- **PowerBI**: Integrated for reporting and business intelligence.
- **Mailgun**: Configured for email services.
- **Rombus**: Integrated for camera/security functionalities.
- **AG Grid**: Enterprise license for advanced table functionalities.
- **OpenAI**: Utilized for in-app AI parsing capabilities.

## Help & Resources Documentation System
- **Location**: Frontend-only content system under `frontend/rea-investment-fe/src/content/help/`
- **Content Model**: Structured TypeScript data files with metadata (slug, title, summary, category, audience, articleType, tags, searchKeywords, relatedArticles, lastUpdated, body)
- **Content Organization**: Articles organized by module (getting-started, home, acquisitions, project-hub, data-room, o-and-m, finance, tasks, reports, portfolio-admin, concepts, reference, troubleshooting), plus FAQ and glossary
- **UI**: Full knowledge-base at `/help` with category browsing grid, client-side search, article detail with markdown rendering, breadcrumbs, table of contents, related articles sidebar, FAQ accordions, and alphabetical glossary
- **Navigation**: URL search params for views (`?article=slug`, `?category=cat`, `?view=faq`, `?view=glossary`, `?q=search`)
- **Contextual Links**: `LearnMoreLink` component at `src/components/common/LearnMoreLink/` used in Finance, O&M, and Reports modules
- **Adding Content**: Add articles to the appropriate file in `src/content/help/articles/`, register in `src/content/help/index.ts`
# iliOS - REA Investment Platform

## Overview
iliOS is a real estate asset investment management platform. It provides comprehensive tools for managing the entire lifecycle of real estate investments, from deal acquisition and due diligence to asset management, financial tracking, and reporting. The platform aims to streamline investment processes, enhance decision-making with data-driven insights, and improve operational efficiency for real estate investors and asset managers.

Key capabilities include:
- **User Authentication and Authorization**: Secure access control.
- **Multi-Company User Membership**: Users can belong to multiple companies with different roles (company_admin, contributor, read_only) without requiring project assignments.
- **Workspace Landing Page**: User-centric dashboard showing accessible companies, projects, and pending tasks.
- **Asset Management**: Tracking and managing real estate assets.
- **Due Diligence**: Tools to support the diligence process for new acquisitions.
- **Task Management**: Organization of investment-related tasks.
- **Financial Management**: Budgeting, obligation tracking, and vendor management.
- **Sales Pipeline Management**: Tracking potential deals from prospecting to conversion.
- **Reporting**: Generating insights and reports on investment performance.

The platform is designed to be a critical tool for real estate professionals, offering a centralized system for investment oversight and operational governance.

## User Preferences
I prefer detailed explanations and thorough documentation for any implemented features or architectural decisions.
I expect iterative development, with clear communication before significant changes are made.
Do not change the fundamental "Site" entity in the backend; use "Project" only as a UI terminology update.

## System Architecture

**Frontend:**
- **Technology Stack**: React 18, TypeScript, Material UI (MUI) for component library, React Query for data fetching, React Router DOM for navigation, AG Grid for complex tables, Chart.js for data visualization, Webpack 5 for bundling.
- **Deployment**: Configured as a static deployment, building the React app and serving static files.
- **UI/UX Decisions**:
    - **Terminology Standardization**: All user-facing content uses "Projects" instead of "Sites" to improve clarity, while backend entities remain `sites`.
    - **Navigation Architecture**:
        1. **Entity Context Navigation (Top Bar)**: Displays `Portfolio → Company → Project` hierarchy, persists selection to `localStorage`, and dynamically enables/disables icons based on selected entity level.
        2. **Module Sidebar Navigation (Left)**: Permission-based visibility for modules like Asset Management, O&M, Due Diligence, Finance, Reports.
        3. **Breadcrumb Navigation (Header)**: Auto-generates from React Router `handle` patterns, resolving dynamic segments from URL parameters.
    - **Context Bar Infrastructure**: Unified three-tier scope management system. See `docs/context_bar_contract.md` for complete specification.
        - **Scope Types**: Portfolio (all entities), Company (single company + its projects), Project (single project)
        - **Dual Route Patterns**: Canonical routes (`/portfolio`, `/companies/:id`, `/projects/:id`) for direct entity access; Module-scoped lens routes (`/[module]/scope/{portfolio|company/:id|project/:id}`) for in-module scope switching
        - **Repaint Navigation**: Switching scope via Context Bar keeps users in current module using lens routes
        - **ScopedModuleRoute Component**: Wrapper that sets context from URL parameters without navigating away from module
        - **Persistence**: Current scope persisted to localStorage with 5-minute React Query cache for accessible entities
    - **Asset Management Overview**: Features a canonical site overview with drag-and-drop reordering, collapsible cards, persistence of state to `localStorage`, an executive summary, an underwriting readiness widget, and enhanced card headers with completeness indicators.
    - **Sidebar Layout Pattern**: Critical guidance for implementing collapsible sidebar navigation, ensuring main content and fixed headers correctly adapt to sidebar width changes using `marginLeft`, `width`, and `maxWidth` properties. Sidebar state is persisted to `localStorage`.
    - **Portfolio Admin Module**: Three-tier administration hierarchy for managing companies, projects, and users:
        - **Portfolio Level** (`/portfolio-admin`): Rollup view of all companies and projects with summary statistics. Actions include Add Company and Add User (portfolio-wide access).
        - **Company Level** (`/portfolio-admin/companies/:id`): Company details, summary cards, quick links to modules, and project list. Actions include Add Project and Add User (company-wide access).
        - **Project Level** (`/portfolio-admin/projects/:id`): Auto-generated project overview with data completeness scoring and readiness assessment. Actions include Add User (project-only access).
        - **Access Warnings**: AddUserDialog displays appropriate warnings about access scope implications when adding users at different levels.
        - **Centralized Entity Management**: All "Add" actions in Settings module redirect to Portfolio Admin to enforce consistent management flows.

**Backend:**
- **Technology Stack**: Python 3.11, FastAPI for API development, SQLAlchemy for ORM, Alembic for database migrations, PostgreSQL as the primary database.
- **Core Modules**:
    - **Workspace Module**: User-centric landing page (`/workspace`) showing summary cards (companies, projects, tasks) and a list of accessible companies with access source indicators. Features context-aware Company Admin page for managing company membership.
    - **Finance Module**: Capital governance, authorization, and compliance engine. Features budget vs. actual tracking, vendor visibility, authorization gating, approval workflows with audit trails, portfolio/fund rollups, and data room package export.
    - **Acquisitions Module** (formerly Sales): Manages a 13-stage deal acquisition pipeline (removed Phase1Diligence, added ClosedWon), tracking deals separately until conversion into "Site" entities (referred to as "Projects" in the UI).
        - **Pipeline Stages**: prospect, nda_signed, inputs_received, modeling, model_review, model_approved, quoted, term_sheet_neg, term_sheet_signed, mipa_negotiating, mipa_signed, closed_won, passed, dead
        - **Conversion-Eligible Stages**: TermSheetSigned OR MIPASigned
        - **System-Constructed Names**: Format `{State}-{CompanyCode}-{Sequence}` (e.g., TX-ACME-0001)
        - **Read-Only Converted Deals**: Deals marked as converted display a banner and navigation to Project Hub
    - **Project Hub Module** (consolidated Asset Management + Due Diligence): Unified project management interface with tabbed navigation.
        - **Tabs**: Overview, Data Room, O&M, Finance, Tasks, Reporting
        - **Lifecycle States**: pre_diligence, due_diligence, implementation, placed_in_service, operations (snake_case aligned frontend/backend)
        - **Lifecycle Transitions**: RBAC-gated (Company Admin or Superuser), audit-logged, auto-creates tasks from templates
        - **Signed Agreement Gating**: Required (uploaded/waived) before advancing past due_diligence lifecycle
        - **Document Extraction Workflow**: source (ai_extraction/manual_entry), status (proposed/accepted/overridden/rejected)
- **Multi-Company Access System**:
    - **UserCompanyAccess Model**: Manages user-company relationships with roles (company_admin, contributor, read_only) and statuses (active, invited, suspended).
    - **Access Source Types**: Direct assignment via UserCompanyAccess, project-inherited via UserProject → parent_company_id, or both.
    - **Authorization**: System users and company admins can manage company membership; regular users can only view members they have access to.
- **Portfolio Hub Boundary Model**: Introduced to fix global portfolio access bug. See `docs/portfolio_hub_model.md` for full specification.
    - **Self-Referencing Hub**: `companies.portfolio_hub_id` column links companies to a hub company (NULL = is a hub)
    - **Hub-Scoped Portfolio Access**: `user_portfolio_access.portfolio_hub_company_id` requires hub selection when granting portfolio access
    - **Bounded Access**: Portfolio users only see companies within their assigned hub(s), not all companies globally
    - **Shared Resources**: DAS connections within a hub are discoverable by all companies in that hub for telemetry setup
    - **Helper Functions**: `app/helpers/portfolio_hub.py` provides `resolve_company_hub_id()`, `get_portfolio_group_company_ids()`, and access checks
- **Architectural Guardrails (Asset Management Overview)**: The Asset Management Overview page is designed as a static site record and readiness surface, intentionally avoiding operational data leakage, telemetry, or live performance data. It clearly defines cross-module boundaries, linking to operations modules for live metrics rather than embedding them.
- **Telemetry Module**: Project-scoped telemetry hookup for connecting Data Acquisition Systems (DAS) directly from the Project → Telemetry tab:
    - **4-Step Wizard**: Connection → Site Mapping → Device Mapping → Confirm/Health flow for guided telemetry setup
    - **Health Monitoring**: Derives telemetry health status from BigQuery device_last_report_ts with thresholds (≤30min=HEALTHY, ≤120min=WARN, >120min=ERROR)
    - **Readiness Strip**: Visual 4-step progress indicator showing connection, site mapping, device mapping, and data flow status
    - **DAS Providers**: Supports KMC (token auth) and Also Energy (username:password base64)
    - **Telemetry-Eligible Devices**: Inverter, module, weather_station categories only
    - **Mapping CRUD**: Site and device mapping with Firestore synchronization via GCP Cloud Functions
    - **Audit Trail**: All telemetry operations (connection, site mapping, device mapping changes) are logged to the audit system
    - **Route**: `/asset-management/companies/:companyId/sites/:siteId/telemetry`
    - **API Endpoints**: `/api/telemetry/sites/:siteId/*` for readiness, health, site/device mappings
    - **Dual-Ownership DAS Connections**: See `docs/telemetry_hub_scoping.md` for full specification
        - **Company-Owned** (`owner_type='company'`): Traditional single-company connections
        - **Portfolio-Shared** (`owner_type='portfolio'`): Connections shared across all companies in a portfolio hub
        - **Hub Boundaries**: All connections, sharing, and discovery constrained to `portfolio_hub_id` boundaries
        - **Grouped Discovery**: `/api/telemetry/connections/available` returns `company_connections` and `portfolio_connections` arrays
        - **Test Status Tracking**: `last_test_at`, `last_test_status`, `last_test_message` track credential validation results
    - **Health Status States**: HEALTHY, WARN, ERROR, NO_DATA, NO_DATA_YET, NOT_CONFIGURED, MAPPED_NO_DEVICES

## External Dependencies
- **PostgreSQL**: Used as the primary relational database (Replit built-in for production, separate setup for development).
- **Redis**: Upstash with TLS, used for caching and session management.
- **PowerBI**: Integrated for reporting and business intelligence.
- **Mailgun**: Configured for email services (US region, domain: iliospower.com).
- **Rombus**: Integrated for camera/security functionalities.
- **AG Grid**: Enterprise license configured for advanced table functionalities.
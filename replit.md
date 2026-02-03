# iliOS - REA Investment Platform

## Overview
iliOS is a real estate asset investment management platform designed to manage the entire lifecycle of real estate investments, from acquisition and due diligence to asset management, financial tracking, and reporting. The platform aims to enhance decision-making through data-driven insights and improve operational efficiency for real estate investors and asset managers.

Key capabilities include secure user authentication, multi-company user membership, a user-centric workspace, comprehensive asset and task management, financial oversight with budgeting and vendor management, sales pipeline tracking, and robust reporting tools. iliOS serves as a centralized system for investment oversight and operational governance for real estate professionals.

## User Preferences
I prefer detailed explanations and thorough documentation for any implemented features or architectural decisions.
I expect iterative development, with clear communication before significant changes are made.
Do not change the fundamental "Site" entity in the backend; use "Project" only as a UI terminology update.

## System Architecture

**Frontend:**
- **Technology Stack**: React 18, TypeScript, Material UI (MUI), React Query, React Router DOM, AG Grid, Chart.js, Webpack 5.
- **UI/UX Decisions**:
    - **Terminology**: Standardized "Projects" in UI, while backend retains "Sites".
    - **Navigation**:
        - **Entity Context Navigation**: Top bar displaying `Portfolio → Company → Project` hierarchy, persisting selection, and dynamic icon enabling.
        - **Module Sidebar Navigation**: Permission-based left sidebar, routing to Project Hub with tab pre-selection.
        - **Breadcrumb Navigation**: Auto-generated from React Router patterns.
        - **3-Click Rule**: All key workflows from home to action completion aim for three or fewer clicks.
    - **Project Hub Navigation**: Centralized project selection via `ProjectPicker` component, `useProjectNavigation` hook for consistent routing, simplified `/project-hub/projects/:siteId/*` routes, and tab-centric module entry.
    - **Context Bar Infrastructure**: Unified three-tier scope management (Portfolio, Company, Project) with dual route patterns (canonical and module-scoped lens routes) and scope persistence to `localStorage`.
    - **Asset Management Overview**: Static site record and readiness surface with drag-and-drop reordering, collapsible cards, executive summary, underwriting readiness, and enhanced card headers.
    - **Sidebar Layout Pattern**: Collapsible sidebar with state persisted to `localStorage`, ensuring main content adapts correctly.
    - **Portfolio Admin Module**: Three-tier administration hierarchy for managing companies, projects, and users with role-based access warnings and centralized entity management. Now serves as the **single authoritative entry point** for all entity management (users, companies, projects). Includes:
        - **Navigation Access**: Avatar dropdown menu item "Portfolio Admin" and left sidebar navigation with AdminPanelSettingsIcon.
        - **Edit Dialogs**: EditCompanyDialog and EditProjectDialog for inline editing from CompanyLevelPage and ProjectLevelPage headers.
        - **Endpoint Lockdown (Phase A Complete)**: All legacy Settings mutation endpoints and routers have been permanently removed. /api/settings/* returns 404. Only Portfolio Admin workspace endpoints (/api/workspace/*) can mutate users, companies, or projects.
    - **Settings Module Consolidation**: Settings page focuses on system configuration only (Health Checks, Notifications, Alerts). All backend Settings routers have been removed; no /api/settings/* endpoints exist.

**Backend:**
- **Technology Stack**: Python 3.11, FastAPI, SQLAlchemy, Alembic, PostgreSQL.
- **Core Modules**:
    - **Workspace Module**: User-centric landing page displaying summary cards and accessible companies, supporting context-aware Company Admin.
    - **Finance Module**: Capital governance engine with budget vs. actual tracking, vendor visibility, authorization, approval workflows with audit trails, and portfolio/fund rollups. Features a dedicated landing page, `SiteFinance` page for CRUD operations, and robust form dialogs for financial entities.
    - **Acquisitions Module**: Manages a 13-stage deal acquisition pipeline, tracking deals until conversion into "Site" entities (referred to as "Projects" in UI). Supports system-constructed names and read-only views for converted deals.
    - **Project Hub Module**: Consolidates asset management and due diligence into a unified interface with tabbed navigation (Overview, Data Room, O&M, Finance, Tasks, Reporting). Manages project lifecycle states (e.g., `pre_diligence`, `due_diligence`) with RBAC-gated transitions, signed agreement gating, and document extraction workflows.
- **Multi-Company Access System**: Manages user-company relationships with roles (company_admin, contributor, read_only) and statuses. Supports direct assignment and project-inherited access.
- **Canonical Effective-Access Resolver (Phase B.1 + C Complete)**: Single authoritative resolver (`app/helpers/access_resolver.py`) for entity-level and module-level authorization checks. **Fully fail-closed** - no legacy fallback exists. Implements:
    - **Eligibility**: Portfolio access covers company/project; Company access covers all projects; Project access covers only that project.
    - **Restrict-Only Semantics**: Most restrictive base role wins (`read_only < contributor < company_admin`); Module permissions are intersected across applicable grants.
    - **Explainability**: Returns `grant_sources` showing which levels contributed (portfolio/company/project) and `reason_code` (always populated).
    - **Decision Contract**: Uses `decision: AccessDecision` (ALLOW/DENY enum) + `reason_code: str`. Never returns undetermined - all paths return allow or deny.
    - **Reason Codes**: `no_access_grants`, `project_company_mismatch`, `undetermined_context`, `system_error`, `missing_module_permission`.
    - **Entity-Level Integration**: `GetAuthorizedEntity` in `project_access.py` is fully authoritative - **no legacy fallback**. Missing context → DENY with `undetermined_context`. Exceptions → DENY with `system_error`. Structured logging with `exc_info=True` for debugging.
    - **Deprecated Parameter**: `additional_company_site_id_access` is ignored; company admins get site access through company-level grants in the hierarchy.
    - **Helpers**: `require_effective_permission()` convenience wrapper; `check_module_permission()` for granular permission checks.
    - **Module-Level Permission Enforcement (Phase C)**: 
        - **Guard Helper**: `app/helpers/permission_guards.py` provides `require_module_permission()` for endpoint protection.
        - **Normalization Rule**: If "edit" is present for a module, "view" is automatically included (enforced in `_normalize_permissions()`).
        - **Router Integration**: Finance routers (budgets, vendors, actuals, obligations) now use resolver-based module permission guards.
        - **Usage Pattern**: 
          ```python
          from app.helpers.permission_guards import require_module_permission
          from app.static.permissions import PermissionsModules
          
          require_module_permission(
              user_id=current_user.id,
              company_id=company_id,
              db_session=db_session,
              module_key=PermissionsModules.finance.value,
              action="view",  # or "edit" for mutations
          )
          ```
        - **Future Work**: Migrate remaining modules (assets_management, diligence, o&m, reporting) from legacy `AuthorizedUser` to new guards.
- **Role Profiles System**: Granular stakeholder role definitions (e.g., executive, asset_manager) augmenting base roles, stored in `role_profiles` table with `applicable_company_types` and `default_module_permissions`. Integrates with `UserCompanyAccess` for custom permissions and dashboard keys.
- **Portfolio Hub Boundary Model**: Introduces `portfolio_hub_id` to link companies within a hub, ensuring portfolio users only see companies within their assigned hub(s). Supports shared resources and provides helper functions for access checks.
- **Architectural Guardrails (Asset Management Overview)**: Designed as a static record, intentionally avoiding operational data leakage, telemetry, or live performance data, and linking to operational modules for live metrics.
- **Telemetry Module**: Project-scoped telemetry hookup for connecting Data Acquisition Systems (DAS) via a 4-step wizard (Connection, Site Mapping, Device Mapping, Confirm/Health). Features health monitoring (deriving status from BigQuery), readiness strip, support for various DAS providers (KMC, Also Energy), and device mapping CRUD with Firestore sync. Supports dual-ownership DAS connections (company-owned vs. portfolio-shared) constrained by `portfolio_hub_id` boundaries.

## External Dependencies
- **PostgreSQL**: Primary relational database.
- **Redis**: Used for caching and session management.
- **PowerBI**: Integrated for reporting and business intelligence.
- **Mailgun**: Configured for email services.
- **Rombus**: Integrated for camera/security functionalities.
- **AG Grid**: Enterprise license for advanced table functionalities.
# iliOS - REA Investment Platform

## Overview
iliOS is a real estate asset investment management platform designed to manage the entire lifecycle of real estate investments, from acquisition and due diligence to asset management, financial tracking, and reporting. The platform aims to enhance decision-making through data-driven insights and improve operational efficiency for real estate investors and asset managers.

Key capabilities include secure user authentication, multi-company user membership, a user-centric workspace, comprehensive asset and task management, financial oversight with budgeting and vendor management, sales pipeline tracking, and robust reporting tools. iliOS serves as a centralized system for investment oversight and operational governance for real estate professionals.

## User Preferences
I prefer detailed explanations and thorough documentation for any implemented features or architectural decisions.
I expect iterative development, with clear communication before significant changes are made.
Do not change the fundamental "Site" entity in the backend; use "Project" only as a UI terminology update.

## System Architecture

### Frontend
- **Technology Stack**: React 18, TypeScript, Material UI (MUI), React Query, React Router DOM, AG Grid, Chart.js, Webpack 5.
- **UI/UX Decisions**:
    - **Terminology**: Standardized "Projects" in UI, while backend retains "Sites".
    - **Navigation**: Implements Entity Context Navigation (`Portfolio → Company → Project`), Module Sidebar Navigation (permission-based), Breadcrumb Navigation, and a "3-Click Rule" for key workflows.
    - **Context Bar Infrastructure**: Unified three-tier scope management (Portfolio, Company, Project) with route patterns and scope persistence.
    - **Asset Management Overview**: Static site record and readiness surface with drag-and-drop reordering, collapsible cards, and executive summary.
    - **Sidebar Layout Pattern**: Collapsible sidebar with state persisted.
    - **Portfolio Admin Module**: Single authoritative entry point for managing companies, projects, and users with role-based access warnings and centralized entity management.
    - **Settings Module Consolidation**: Settings page focuses on system configuration only, with all backend Settings routers removed.

### Backend
- **Technology Stack**: Python 3.11, FastAPI, SQLAlchemy, Alembic, PostgreSQL.
- **Core Modules**:
    - **Workspace Module**: User-centric landing page with summary cards and accessible companies.
    - **Finance Module**: Capital governance engine with budget vs. actual tracking, vendor management, authorization, and approval workflows.
    - **Acquisitions Module**: Manages a 13-stage deal acquisition pipeline, tracking deals until conversion into "Site" entities (referred to as "Projects" in UI).
    - **Project Hub Module**: Consolidates asset management and due diligence into a unified interface with tabbed navigation and manages project lifecycle states with RBAC-gated transitions.
- **Multi-Company Access System**: Manages user-company relationships with roles and statuses, supporting direct assignment and project-inherited access.
- **Canonical Effective-Access Resolver**: Single authoritative resolver for entity-level and module-level authorization checks, implementing fail-closed eligibility, restrict-only semantics, and detailed explainability with decision contracts and reason codes. All legacy access mechanisms are deprecated.
- **Module-Level Permission Enforcement**: Uses `app/helpers/permission_guards.py` for endpoint protection, normalizing permissions (e.g., "edit" implies "view"), and integrating with router endpoints for granular permission checks.
- **Diligence Module Migration (Phase C.2)**: All 26 Diligence endpoints migrated to canonical permission guards with `require_module_permission()`. Routers: `documents.py` (10 endpoints), `files.py` (7 endpoints), `files_parsing.py` (3 endpoints), `co_terminus.py` (4 endpoints), `agreements.py` (2 endpoints). All endpoints use project-scoped authorization (company_id + project_id context). List endpoints are scoped to specific site via `get_authorized_site` dependency.
- **Phase D Cross-Module Integration Tests**: Comprehensive integration tests verifying authorization behavior across Finance, Asset Management, and Diligence modules. Tests cover: (A) finance:view enforcement, (B) finance:edit enforcement, (C) assets_management:edit enforcement, (D) diligence:view enforcement, (E) restrict-only intersection via role_profiles, (F) project-only access scoping. Standardized 403 payload assertions verify error, reason_code, module_key, action, and grant_sources_summary fields. Debug endpoint security tests verify cross-company admin rejection and non-admin rejection.
- **Role Profiles System**: Granular stakeholder role definitions augmenting base roles, stored in `role_profiles` table with default module permissions and integration with `UserCompanyAccess`.
- **Portfolio Hub Boundary Model**: Introduces `portfolio_hub_id` to link companies within a hub, ensuring portfolio users only see companies within their assigned hub(s).
- **Architectural Guardrails (Asset Management Overview)**: Designed as a static record, intentionally avoiding operational data leakage, telemetry, or live performance data, linking to operational modules for live metrics.
- **Telemetry Module**: Project-scoped telemetry hookup for connecting Data Acquisition Systems (DAS) via a 4-step wizard, featuring health monitoring, readiness strip, support for various DAS providers (KMC, Also Energy), and device mapping CRUD with Firestore sync. Supports dual-ownership DAS connections constrained by `portfolio_hub_id` boundaries.

## External Dependencies
- **PostgreSQL**: Primary relational database.
- **Redis**: Used for caching and session management.
- **PowerBI**: Integrated for reporting and business intelligence.
- **Mailgun**: Configured for email services.
- **Rombus**: Integrated for camera/security functionalities.
- **AG Grid**: Enterprise license for advanced table functionalities.
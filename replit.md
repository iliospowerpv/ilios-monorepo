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
- **Data Room PDF Viewer & Evidence Navigation**: Implements a hybrid PDF/document viewer with programmatic page navigation, text search, and highlighting. It links AI-extracted fields to specific pages and snippets within documents for evidence-based verification.
- **Data Room Evidence & Acceptance Workflow**: Provides an audit trail for AI-extracted evidence, a sequential verification workflow, and bulk acceptance capabilities for managing extracted data.

### Backend
- **Technology Stack**: Python 3.11, FastAPI, SQLAlchemy, Alembic, PostgreSQL.
- **Core Modules**: Workspace, Finance (capital governance, budgeting, vendor management), Acquisitions (13-stage deal pipeline), and Project Hub (unified asset management and due diligence).
- **Access Control**: Multi-Company Access System with granular authorization using a Canonical Effective-Access Resolver and Module-Level Permission Enforcement. Includes a Role Profiles System for detailed stakeholder definitions and a Portfolio Hub Boundary Model for data visibility.
- **Architectural Guardrails**: Asset Management Overview functions as a static record, linking to operational modules for live metrics.
- **Telemetry Module**: Project-scoped telemetry for Data Acquisition Systems (DAS) integration, health monitoring, and device mapping CRUD with Firestore sync.
- **Document Versioning & Promotion System**: Manages lender-quality Data Room document versions with a "Promote to Current Assumptions" workflow, supporting `candidate`, `active`, and `retired` `ProjectFact` states with atomic transactions and diff computation.
- **Extraction Registry & Prompt Studio**: A scalable system for dynamic document type and field configuration using database-driven schemas, prompt templates, and an `ExtractionPipelineService`. Supports re-extraction workflows with binding snapshots and includes an Admin API and UI.
- **In-App AI Parsing**: Fully in-app document parsing using Replit AI Integrations (OpenAI), eliminating external cloud function dependencies. Features an `InAppParsingService` for file handling, text extraction (PDF, DOCX), LLM calls via FastAPI BackgroundTasks, observability with correlation IDs, and retry logic.
    - **Idempotency & Concurrency Safety**: Prevents duplicate parsing and race conditions using `queued` statuses, atomic claims with `SELECT ... FOR UPDATE` row locking, and partial unique indexes.
    - **Quality Guardrails & Resource Limits**: Enforces configurable settings for minimum text characters, maximum file size, maximum PDF pages, and maximum characters sent to the LLM. It includes `ParsingReasonCode` enum for machine-readable failure identifiers and provides extraction metadata.
- **Storage Service Abstraction**: Replit-native storage architecture with an abstract `StorageService` interface, supporting `ReplitStorageService`, optional `GCSStorageService`, and `HybridStorageService` for migration.
- **Data Room Acceptance Safety & Parse Run History**: Implements a parse run history panel for files and enforces acceptance safety rules, validating `run_id` and run status before allowing bulk acceptance of extracted data.
- **Project Summary Panel (Embedded in Data Room)**:
    - **Location**: Top of Project Hub → Data Room page (`AssetManagementSiteDetails/tabs/DataRoom/DataRoom.tsx`)
    - **Component**: `ProjectSummaryPanel` - Collapsible panel providing cross-document analysis
    - **Features**:
        - **Terms & Values Section**: Roll-up of extracted agreement terms with document type selector (reuses agreement types API)
        - **Cross-Document Checks Section**: Co-terminus check status with summary chips (Equal/Not Equal/N/A counts), Run/Rerun button
        - **Collapsible State**: Persists expand/collapse per user+project via localStorage (`project-summary-expanded-{siteId}`)
        - **Permission Gating**: Hidden entirely if user lacks `diligence:view`; Run/Rerun button requires `diligence:edit`
        - **Collapsed Health Summary (Phase B5.1)**: Project-level due diligence health indicator with:
            - Leading health chip: "Due Diligence: Healthy/In Progress/Attention Needed"
            - Documents: "X/Y reviewed" (documents_with_promoted_terms / documents_total from summary-stats endpoint)
            - Terms: "Z promoted" (promoted_terms_total from summary-stats endpoint)
            - Co-terminus: "OK/Not run/Running/X mismatches" chip
        - **Summary Stats Endpoint (Phase B5.1.1)**: `/api/due-diligence/sites/{site_id}/summary-stats` provides project-level aggregate metrics:
            - `documents_total`: Count of all non-archived documents for the site (role-agnostic for consistent project health)
            - `documents_with_promoted_terms`: Distinct documents with active promoted facts (via File or DocumentKey paths)
            - `promoted_terms_total`: Count of active, unsuperseded facts with meaningful values
            - `coterminus`: Status, mismatches, and last_run_at from CoTerminusCheck
        - **Design Decision**: Summary stats are intentionally role-agnostic to provide consistent project health metrics regardless of viewer role. Different users seeing different totals would make health indicators meaningless.
    - **APIs Used**: `/agreements/`, `/agreements/{id}/terms`, `/co-terminus/check`, `/co-terminus/status`, `/due-diligence/sites/{site_id}/summary-stats`
    - **No New Routes**: Panel is embedded, not a separate page

## Roles & Scope Contract (Closed)
This section defines the stable authorization contract that all modules (Finance, Diligence, Assets, etc.) rely on. No new roles or permission models will be introduced without explicit approval.

### Base Roles
The system uses exactly three base roles, ordered by restrictiveness:
| Role | Level | Description |
|------|-------|-------------|
| `read_only` | Least privileged | Can view permitted modules; cannot make changes |
| `contributor` | Mid-tier | Can view and edit permitted modules |
| `company_admin` | Most privileged | Full access to permitted modules; can manage memberships |

### Role Profiles
Role profiles augment base roles by providing **restrict-only** module permission overrides. They are used for deeper stakeholder definitions (e.g., "Investor" profile that restricts access to only Reporting and Finance modules).

**Key Rules**:
- Role profiles can only **narrow** permissions, never expand them
- Permissions are computed via **intersection** across all applicable grants
- If a role profile restricts a module, access is denied even if the base role would allow it
- Role profile is optional; if not set, base role defaults apply

### Access Grant Hierarchy
Access grants follow the Portfolio → Company → Project hierarchy:

| Grant Level | Stored In | Covers |
|-------------|-----------|--------|
| Portfolio | `user_portfolio_access` | All companies and projects within the portfolio |
| Company | `user_company_access` | Single company and all its projects |
| Project | `user_project` | Single project only |

**Resolution Rules**:
1. Collect all applicable grants for the target resource
2. `effective_base_role` = **MOST RESTRICTIVE** role among applicable grants
3. `effective_module_permissions` = **INTERSECTION** of permissions across grants
4. If any grant denies a module, access is denied (restrict-only semantics)

### Scope Semantics Table
| Action | Portfolio Level | Company Level | Project Level |
|--------|-----------------|---------------|---------------|
| View entity | Via portfolio grant | Via company or portfolio grant | Via project, company, or portfolio grant |
| Edit metadata | company_admin role + module:edit | company_admin role + module:edit | company_admin role + module:edit |
| Manage membership | company_admin role | company_admin role | company_admin role |
| Configure integrations | company_admin role + settings permission | company_admin role + settings permission | N/A (project-level inherits company) |
| Module mutations (Diligence/Assets/Finance) | Requires module:edit + entity access | Requires module:edit + entity access | Requires module:edit + entity access |

### Module Permission Keys
| Module Key | Description |
|------------|-------------|
| `Asset Management` | Project hub, site management, asset overview |
| `Finance` | Budgets, vendors, actuals, obligations |
| `Diligence` | Data room, document parsing, agreements |
| `Reporting` | Reports, analytics, dashboards |
| `O&M` | Operations and maintenance, alerts |

### Canonical Authorization Components
- **Resolver**: `app/helpers/access_resolver.py` - `resolve_effective_access()` is the single source of truth
- **Guards**: `app/helpers/permission_guards.py` - `require_module_permission()` and `require_module_permission_any_context()`
- **Error Format**: All 403 responses include `reason_code`, `module_key`, `action`, and `grant_sources`

### Explicit Non-Goals
- **Roles do NOT imply responsibility/ownership/workflow status**: A "contributor" role does not mean the user is assigned to a task; use task assignments separately
- **Contacts/Organizations do NOT grant access**: The Contacts system is an address book; contact records have no bearing on authorization
- **No cascading permissions**: Access is explicit per grant; portfolio access covers child entities, but child grants do not affect parent access

### System User Bypass
Users with `is_system_user=True` bypass all permission checks. This is reserved for internal service accounts and admin operations.

## External Dependencies
- **PostgreSQL**: Primary relational database.
- **Redis**: Used for caching and session management.
- **PowerBI**: Integrated for reporting and business intelligence.
- **Mailgun**: Configured for email services.
- **Rombus**: Integrated for camera/security functionalities.
- **AG Grid**: Enterprise license for advanced table functionalities.

## Contacts System (CRM-style Address Book)
A CRM-style contact management system for tracking external people related to portfolio, company, and project entities. Contacts are **not** platform users—they are address book entries for external stakeholders like brokers, vendors, investors, or other third parties.

### Key Design Decisions
- **Contacts are NOT Users**: Contacts are address book entries completely separate from authentication and access control. A contact may optionally match a platform user by email (indicated by `is_user` flag), but this grants no permissions.
- **Scope-Based Storage**: Contacts are stored at three levels (portfolio, company, project) with exact-scope filtering (no inheritance/cascading).
- **Case-Insensitive Email Uniqueness**: Email addresses are unique per scope using partial unique indexes on `email_normalized`.
- **Soft Delete via Archive**: Contacts can be archived instead of deleted, preserving history.

### Backend Implementation
- **Migration**: `ff08_add_contacts_table.py` - Creates `contacts` table with `contact_scope_type` enum, scope foreign keys, and partial unique indexes for email uniqueness.
- **Model**: `app/models/contact.py` - SQLAlchemy model with scope-based FK validation constraint.
- **Schema**: `app/schema/contact.py` - Pydantic schemas for CRUD operations with computed `is_user` field.
- **Router**: `app/routers/contacts.py` - Full CRUD API with search, permission checks, and is_user computation via email matching.

### Frontend Implementation
- **API Client**: `src/api/contacts.ts` - TypeScript API client for contacts CRUD.
- **Components**: 
  - `ContactFormModal` - Create/edit contact dialog with tags support
  - `ContactsList` - Searchable table with archive/delete actions and is_user indicator
- **Integration**: Contacts section added to CompanyLevelPage and ProjectLevelPage in Portfolio Admin.

### API Endpoints
- `GET /api/contacts` - List contacts with scope filtering and search
- `POST /api/contacts` - Create contact
- `GET /api/contacts/{id}` - Get single contact
- `PATCH /api/contacts/{id}` - Update contact
- `DELETE /api/contacts/{id}` - Permanently delete contact

### Permission Model
- Contacts follow the same permission model as other Portfolio Admin features
- Access is controlled via company/project membership
- System users have full access to all contacts
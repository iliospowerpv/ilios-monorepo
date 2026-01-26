# iliOS - REA Investment Platform

## Overview
This is a real estate asset investment management platform built with React and TypeScript frontend, and Python FastAPI backend. The application provides user authentication, asset management, due diligence, task management, and reporting features.

## Project Structure
- `frontend/rea-investment-fe/` - React/TypeScript frontend application
  - `src/` - Source code (components, modules, hooks, contexts)
  - `config/` - Webpack and development server configuration
  - `public/` - Static assets
  - `scripts/` - Build and development scripts
- `backend/ilios-server/` - Python FastAPI backend
  - `app/` - Main application code
  - `alembic/` - Database migrations
- `backend/ilios-DocAI/` - AI/ML document processing service
- `docai/` - Document AI processing components

## Development Workflows

### Frontend (Port 5000)
```bash
cd frontend/rea-investment-fe && PORT=5000 npm start
```

### Backend (Port 8000)
```bash
cd backend/ilios-server && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Environment Variables
- **REACT_APP_URL**: Backend API URL for frontend to connect to
- **db_host, db_user, db_password, db_name**: Database connection for development
- Production uses Replit's built-in PostgreSQL (PG* environment variables)

## Test Credentials
- Email: system@user.com
- Password: SystemUser123!

## Tech Stack

### Frontend
- React 18
- TypeScript
- Material UI (MUI)
- React Query (TanStack Query)
- React Router DOM
- AG Grid (tables)
- Chart.js
- Webpack 5

### Backend
- Python 3.11
- FastAPI
- SQLAlchemy
- Alembic (migrations)
- PostgreSQL

## Deployment
Configured as a static deployment for frontend:
1. Runs `npm run build` in the frontend directory
2. Serves the built static files from `frontend/rea-investment-fe/build`

## Notes
- Both frontend and backend are configured and running in this Replit environment
- Frontend connects to the backend API on port 8000

## Recent Features

### Finance Module MVP (Jan 2026)
A capital governance, authorization, and compliance engine (NOT a general ledger) that provides:
- **Budget vs Actual Tracking**: Site-level and portfolio-level budget management with variance analysis
- **Vendor/Service Provider Visibility**: Centralized vendor registry with contact info and type classification
- **Authorization Gating**: Prerequisite checks (ownership, interconnection, insurance, PTO/COD dates) before payment authorization
- **Approval Workflows with Audit Trail**: Submit → Approve/Reject/Override flow with full audit history
- **Portfolio/Fund Rollup**: Company-level aggregation showing finance readiness across all sites
- **Data Room Package Export**: JSON export of finance data for investor/lender due diligence

**Backend Components**:
- `app/models/finance.py` - SQLAlchemy models (FinanceVendor, FinanceBudget, FinanceBudgetLineItem, FinanceObligation, FinanceApproval, FinanceActual)
- `app/schema/finance.py` - Pydantic schemas for API request/response
- `app/routers/finance/` - API routes (vendors, budgets, obligations, actuals, portfolio)
- `app/crud/finance.py` - Database CRUD operations
- `app/static/permissions.py` - FinancePermissions RBAC class

**Frontend Components**:
- `src/modules/finance/` - Finance module directory
- `pages/FinanceHome/` - Portfolio overview with summary cards and site list
- `pages/SiteFinance/` - Site-level finance with tabs (Budget, Obligations, Vendors, Actuals)
- `api/finance.ts` - API client with React Query hooks
- `types/index.ts` - TypeScript types and enums

**API Routes** (all prefixed with `/api/finance/companies/{company_id}/`):
- `GET /portfolio/summary` - Portfolio-level finance summary
- `GET /portfolio/sites/{site_id}/summary` - Site-level finance summary
- `GET/POST /vendors` - Vendor CRUD
- `GET/POST /budgets` - Budget CRUD with line items
- `GET/POST /obligations` - Obligation management
- `POST /obligations/{id}/submit` - Submit for approval
- `POST /obligations/{id}/approve` - Approve/reject/override
- `GET /actuals` - Actual transactions (supports QuickBooks/Gravity import stubs)
- `GET /portfolio/sites/{site_id}/data-room-package` - Export finance data

**Navigation**: Enabled at `/finance` with Finance permission check in NavMenu.tsx

### Sales Module MVP (Jan 2026)
14-stage deal acquisition pipeline with conversion to projects. Tracks deals separately from Site entities until they are ready for due diligence.

**Pipeline Stages (14)**: prospect → nda_signed → inputs_received → modeling → model_review → model_approved → quoted → term_sheet_neg → term_sheet_signed → phase_1_diligence → mipa_negotiating → mipa_signed → passed → dead

**Lifecycle States**: sales_pre_diligence → due_diligence → implementation → placed_in_service → operations

**Key Entities**:
- **Deal**: Pre-project entity for acquisition tracking. Contains developer info, financial metrics, location, and project dates.
- **Site**: Created when a deal is converted to a project via "Convert to Project" action.

**Backend Components**:
- `app/models/sales.py` - Deal and SalesStateTransition models
- `app/schema/sales.py` - Pydantic schemas (DealCreate, DealUpdate, DealResponse, SalesPipelineResponse)
- `app/routers/sales/` - API routes (pipeline, projects)
- `app/crud/sales.py` - Database operations
- `app/static/sales.py` - Enums (SalesStage, LifecycleState)

- `app/routers/sales/deals.py` - Deal CRUD and conversion endpoints

**Frontend Components**:
- `src/modules/sales/` - Sales module directory
- `pages/SalesHome/` - Kanban pipeline view with 14 stages, Add Deal dialog
- `pages/DealDetail/` - Deal detail page with edit, stage change, and Convert to Project
- `api/sales.ts` - API client (salesApi for projects, dealsApi for deals)
- `types/index.ts` - TypeScript types and enums

**API Routes** (prefixed with `/api/sales/`):
- `GET /deals/pipeline` - Deal kanban pipeline view (14 stages)
- `GET /deals` - List deals with filters
- `POST /deals` - Create new deal
- `GET/PATCH /deals/{deal_id}` - Deal details/update
- `POST /deals/{deal_id}/stage-transition` - Move deal between pipeline stages
- `POST /deals/{deal_id}/convert-to-project` - Convert deal to Site entity
- `GET /deals/{deal_id}/transitions` - Deal audit log
- `GET/PATCH /projects/{site_id}` - Project details/update (for converted deals)

**Handoff Checklist Required Fields**: address, system_size_ac, system_size_dc, utility_rate, ownership_structure, offtaker_name

**Navigation**: Enabled at `/sales` with Sales permission check in NavMenu.tsx

### Cross-Module Navigation Architecture (Jan 2026)
A three-tier navigation system providing consistent navigation across all modules:

**1. Entity Context Navigation (Top Bar)**
- Component: `EntityContextNav.tsx` in PageHeader
- Displays Portfolio → Company → Project hierarchy with icons
- Persists selection to localStorage (key: `ilios_entity_context`)
- Context-aware: icons enable/disable based on selected entity level
- Clicking icons navigates to the appropriate level within the current module

**2. Module Sidebar Navigation (Left)**
- Component: `PageSidebar.tsx` with `NavMenu.tsx`
- Shows modules: Asset Management, O&M, Due Diligence, Finance, Reports
- Permission-based visibility (checks user permissions per module)
- Active state tracked by URL path

**3. Breadcrumb Navigation (Header)**
- Uses React Router's `handle` pattern with `RouteHandle` type
- Each route defines breadcrumb config via `createRouteHandle()` function
- Breadcrumbs auto-generate from route hierarchy
- Dynamic segments resolved from URL params

**Key Components**:
- `EntityContextProvider` - React context for entity state management (contexts/entityContext/)
- `EntityContextNav` - Icon navigation component (components/layout/EntityContextNav/)
- `createRouteHandle()` - Utility for consistent breadcrumb configuration (handles/handles.ts)

**Entity Context Updates**:
All company/site detail pages update entity context automatically:
- Asset Management: AssetManagementCompanyDetails, AssetManagementSiteDetails
- O&M: CompanyDetails, SiteDetails
- Due Diligence: SiteDetails
- Finance: FinanceHome, SiteFinance

### Asset Management Overview - Investor/Lender Diligence Workflow (Jan 2026)
- **Drag-and-drop reordering**: Cards can be reordered using @dnd-kit library with rectSortingStrategy for grid layouts
- **Collapsible cards**: Each card has a collapse/expand toggle in the header
- **Default state**: Top 2 cards (Site Level Details + Key Dates) open by default, others collapsed
- **Persistence**: Card order and collapsed state persist per site using localStorage (key: `overview_cards_{siteId}`)
- **Executive Summary**: Non-collapsible header showing Site Name, Project ID, Status, Location, System Size, Utility, Key Dates
- **Underwriting Readiness Widget**: Shows Ready/Not Ready status based on 5 critical cards, displays top 3 missing fields
- **Enhanced Card Headers**: Completeness indicators, inline summaries when collapsed, tooltips for missing fields
- **Single Edit Button**: Consolidated edit interaction at bottom of each card in view mode
- **Components**: ExecutiveSummary.tsx, UnderwritingReadiness.tsx, DraggableCardLayout.tsx, Overview.tsx, InformationCardBase.tsx

#### Architectural Guardrails for Canonical Site Overview
1. **No operational data leakage** - This page is a static site record and readiness surface. It must not require telemetry, alerts, or live performance data to be useful.
2. **Clear cross-module boundaries** - Where operational metrics exist, link out to the Operations module. Do not embed time-series charts or live KPIs in the Canonical Site Overview.

### UI Terminology Standardization (Jan 2026)
All user-facing content now uses "Projects" terminology instead of "Sites":
- **Updated labels**: Navigation tabs, table column headers, page titles, form labels, search placeholders, breadcrumbs
- **Affected modules**: Asset Management, O&M, Due Diligence, Finance, Reports, Settings, My Portfolio
- **Preserved identifiers**: API endpoints, variable names (`site_id`, `total_sites`), database fields remain unchanged for backward compatibility
- **Key changes**: "Number of Sites" → "Number of Projects", "Add Site" → "Add Project", "Search by Site Name" → "Search by Project Name"

## Integration Status
- **Redis**: ✅ Working (Upstash with TLS) - Health check at `/api/internal/health`
- **PostgreSQL**: ✅ Working (Replit built-in)
- **PowerBI**: ✅ Working - Returns reports from workspace
- **Mailgun**: ✅ Configured (US region, domain: iliospower.com)
- **Rombus**: ✅ Configured - Camera/security integration
- **AG Grid**: ✅ Licensed - Enterprise license configured

## Tips
- **Upstash copy/paste**: Always paste URLs to a text editor first to verify completeness. The Upstash console copy function may truncate URLs.

## Operational Guidance

### Sidebar Layout Pattern (Critical for All Applications)
When implementing a collapsible sidebar navigation with a fixed position:

1. **Main content must respond to sidebar width changes**:
   - The main content area MUST set both `marginLeft` AND `width` based on sidebar state
   - Use: `marginLeft: sidebarWidth` AND `width: calc(100% - sidebarWidth)`
   - Without explicit width, the main content will be overlapped by the fixed sidebar

2. **Centralized width constants**:
   - Define sidebar widths as constants (e.g., `SIDEBAR_WIDTH_OPEN = 30`, `SIDEBAR_WIDTH_CLOSED = 8`)
   - Use the same constants in both sidebar styles and main content styles

3. **Required CSS properties for main content**:
   ```typescript
   {
     marginLeft: sidebarWidth,
     width: `calc(100% - ${sidebarWidth})`,
     maxWidth: `calc(100% - ${sidebarWidth})`,
     boxSizing: 'border-box',
     transition: theme.transitions.create(['margin-left', 'width', 'max-width'], {...})
   }
   ```

4. **Sidebar state persistence**:
   - Always persist sidebar open/closed state to localStorage
   - Never auto-close sidebar on navigation clicks - let user control it via toggle button only

**Files to check**: `Main.styles.ts`, `PageHeader.styles.ts`, `PageSidebar.styles.ts`, sidebar context/provider

**Note**: Both the main content area AND the fixed header must respond to sidebar width changes. The header uses the same pattern with `left` and `width` properties.

### Project vs Site Terminology (Critical Architecture Note)

**"Project" is a UI terminology change ONLY - NOT a new entity.**

| Aspect | Implementation |
|--------|---------------|
| **Database Entity** | `sites` table (canonical, unchanged) |
| **Primary Key** | `id` (column name in sites table) |
| **FK Convention** | Other tables use `site_id` → `sites.id` |
| **User-Facing Label** | "Project" (displayed in UI text) |
| **API Endpoints** | Use `/sites/` or `:siteId` params (preserved for backward compatibility) |
| **Variable Names** | Use `site_id`, `siteId`, `siteDetails` (internal identifiers) |
| **Junction Table** | `UserProject` - for user access control, NOT a separate entity |

**DO NOT:**
- Create a separate `projects` table
- Create `project_id` as a new identifier
- Duplicate the Site model under a different name
- Build pipeline/deal entities as "Projects"

**Lifecycle States** (on `SiteAdditionalFieldList.status`):
- `Construction` - Project under construction
- `Placed in Service` - Operational, telemetry available
- `Decommissioned` - No longer active
- `Sold` - Ownership transferred

These states control contextual UI messaging and action availability, NOT global navigation visibility. All modules remain visible in the sidebar regardless of lifecycle state.

# Sales Module - Roadmap Notes

## Overview
The Sales module provides pipeline management and lifecycle tracking for solar projects from initial discovery through handoff to Due Diligence.

## Current Implementation Status

### Backend (Complete)
- **Models**: SalesStateTransition for audit logging, extended SiteAdditionalFieldList with sales fields
- **Enums**: SalesStage (discovery, qualified, loi_term_sheet, under_contract, handoff_to_diligence) and LifecycleState (sales_pre_diligence, due_diligence, implementation, placed_in_service, operations)
- **CRUD Operations**: Pipeline queries, project updates, stage/lifecycle transitions
- **API Routes**: `/api/sales/pipeline`, `/api/sales/list`, `/api/sales/projects/{site_id}/...`
- **Handoff Validation**: Server-side checklist validation before allowing handoff_to_diligence transition

### Frontend (In Progress)
- **Types/API**: Complete TypeScript types and API client
- **SalesHome**: Kanban view with toggle for list view (list view placeholder)
- **Navigation**: Integrated in NavMenu with TrendingUpIcon
- **Remaining**: Handoff checklist UI, project detail view, lifecycle transition controls

## Architecture Decisions

### "Project" is UI Terminology Only
- Database entity remains `sites` table
- Primary key: `id` (sites.id)
- Foreign keys: `site_id` pointing to sites.id
- All API endpoints use `/sites/` or `:siteId` params
- Variable names use `site_id`, `siteId` internally

### Lifecycle State Gating
- Navigation items remain visible regardless of lifecycle state
- Module activation/access gated by lifecycle state
- Sales module active during `sales_pre_diligence` lifecycle
- After handoff, project moves to `due_diligence` state

### Handoff Checklist
Required fields before transitioning to Due Diligence:
1. Address
2. System Size AC
3. System Size DC
4. Utility Rate
5. Ownership Structure
6. Offtaker Name

## API Endpoints

### Pipeline
- `GET /api/sales/pipeline?company_id={id}` - Get kanban pipeline view
- `GET /api/sales/list?stage={stage}&lifecycle_state={state}` - Get list view with filters

### Projects
- `GET /api/sales/projects/{site_id}` - Get project details
- `PATCH /api/sales/projects/{site_id}` - Update sales fields
- `POST /api/sales/projects/{site_id}/stage-transition` - Transition sales stage
- `POST /api/sales/projects/{site_id}/lifecycle-transition` - Transition lifecycle state
- `GET /api/sales/projects/{site_id}/handoff-checklist` - Get checklist status
- `GET /api/sales/projects/{site_id}/transitions` - Get audit log
- `GET /api/sales/projects/{site_id}/data-room-package` - Export for diligence

## Future Roadmap

### Phase 2: Enhanced UI
- [ ] Project detail page with inline editing
- [ ] Handoff checklist component with field completion UI
- [ ] Lifecycle transition modal with confirmation
- [ ] List view with AG Grid
- [ ] Drag-and-drop kanban with stage reordering

### Phase 3: Integration
- [ ] Email notifications on stage transitions
- [ ] CRM integration (Salesforce, HubSpot)
- [ ] Document attachment to deals
- [ ] Pipeline forecasting and reporting

### Phase 4: Analytics
- [ ] Conversion rates by stage
- [ ] Time-in-stage analytics
- [ ] Revenue pipeline forecasting
- [ ] Sales team performance dashboards

## Files Reference

### Backend
- `backend/ilios-server/app/models/sales.py` - SalesStateTransition model
- `backend/ilios-server/app/schema/sales.py` - Pydantic schemas
- `backend/ilios-server/app/crud/sales.py` - Database operations
- `backend/ilios-server/app/routers/sales/` - API routes
- `backend/ilios-server/app/static/sales.py` - Enums (SalesStage, LifecycleState)

### Frontend
- `frontend/rea-investment-fe/src/modules/sales/types/index.ts` - TypeScript types
- `frontend/rea-investment-fe/src/modules/sales/api/sales.ts` - API client
- `frontend/rea-investment-fe/src/modules/sales/pages/SalesHome/` - Main page
- `frontend/rea-investment-fe/src/modules/sales/ModuleContainer.tsx` - Module wrapper

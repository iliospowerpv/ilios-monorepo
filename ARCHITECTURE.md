# iliOS Architecture Documentation

This document provides a comprehensive overview of the iliOS real estate asset investment platform architecture to facilitate efficient development and maintenance.

## Table of Contents
1. [Project Overview](#project-overview)
2. [Directory Structure](#directory-structure)
3. [Frontend Architecture](#frontend-architecture)
4. [Backend Architecture](#backend-architecture)
5. [Database Schema](#database-schema)
6. [API Routes (Complete)](#api-routes-complete)
7. [Third-Party Integrations](#third-party-integrations)
8. [Authentication Flow](#authentication-flow)
9. [Key Files Reference](#key-files-reference)
10. [Development Workflows](#development-workflows)

---

## Project Overview

iliOS is a real estate asset investment management platform providing:
- User authentication and role-based access control
- Asset management (companies, sites, devices)
- Due diligence document processing with AI
- Operations and maintenance tracking
- Task management with Kanban boards
- PowerBI reporting integration
- Security camera monitoring (Rombus integration)
- Investor dashboards
- Telemetry data collection and visualization

**Tech Stack:**
- **Frontend:** React 18, TypeScript, Material UI (MUI), React Query, AG Grid Enterprise
- **Backend:** Python 3.11, FastAPI, SQLAlchemy, Alembic
- **Database:** PostgreSQL (Replit built-in / Neon-backed)
- **Cache:** Redis (Upstash with TLS)
- **AI/ML:** Document AI processing service (ilios-DocAI)
- **Cloud:** Google Cloud Platform (GCS, BigQuery, Cloud Functions)

---

## Directory Structure

```
/
├── frontend/
│   └── rea-investment-fe/              # React frontend application
│       ├── src/
│       │   ├── api/                    # API client functions (18 files)
│       │   ├── components/             # Reusable UI components
│       │   │   ├── charts/             # Chart components (Chart.js)
│       │   │   ├── clusters/           # Complex component clusters
│       │   │   ├── common/             # Shared components (tables, loaders, inputs)
│       │   │   ├── forms/              # Form input components
│       │   │   ├── layout/             # Layout components (12 components)
│       │   │   └── modals/             # Modal dialogs
│       │   ├── contexts/               # React contexts (4 contexts)
│       │   ├── hooks/                  # Custom React hooks (6 directories)
│       │   ├── modules/                # Feature modules (10 modules)
│       │   ├── pages/                  # Route page components (10 pages)
│       │   └── utils/                  # Utility functions
│       ├── config/                     # Webpack configuration
│       └── public/                     # Static assets
│
├── backend/
│   ├── ilios-server/                   # Main FastAPI backend (PRIMARY)
│   │   ├── app/
│   │   │   ├── routers/                # API route handlers (21 router files)
│   │   │   ├── models/                 # SQLAlchemy ORM models (23 models)
│   │   │   ├── schema/                 # Pydantic schemas (39 files)
│   │   │   ├── crud/                   # Database CRUD operations (43 files)
│   │   │   ├── helpers/                # Business logic helpers (35+ files)
│   │   │   ├── middlewares/            # Request middlewares
│   │   │   ├── filters/                # Query filters
│   │   │   ├── db/                     # Database configuration
│   │   │   ├── redis_cache/            # Redis caching layer
│   │   │   ├── bigquery/               # BigQuery data sync
│   │   │   └── static/                 # Static configuration files
│   │   └── alembic/                    # Database migrations
│   │
│   ├── ilios-DocAI/                    # AI document processing service
│   │   └── src/
│   │       ├── chatbot/                # Chatbot with LLM
│   │       │   ├── agent/              # Agent logic
│   │       │   ├── prompt_templates/   # LLM prompts
│   │       │   └── validation/         # Response validation
│   │       ├── doc_ai/                 # Document AI processing
│   │       ├── embeddings/             # Vector embeddings (Vertex AI)
│   │       ├── gen_ai/                 # Generative AI utilities
│   │       └── deployment/             # Cloud deployment
│   │           ├── cloud_function/     # GCP Cloud Functions
│   │           ├── cloud_run_job/      # GCP Cloud Run Jobs
│   │           └── fast_api/           # FastAPI deployment
│   │
│   ├── ilios-services/                 # Shared utility services
│   │   ├── common/                     # Common utilities
│   │   └── services/                   # Service implementations
│   │
│   └── rea-telemetry/                  # Telemetry data service
│       └── telemetry/                  # Telemetry processing
│
├── infra/
│   └── ilios-infra/                    # Infrastructure as Code
│       ├── bootstrap/                  # GCP bootstrap scripts
│       ├── ilios-infra/                # Terraform/Pulumi configs
│       └── org-level/                  # Organization-level configs
│
└── docai/                              # Document AI components (legacy)
```

---

## Frontend Architecture

### Feature Modules (`src/modules/`)

Each module represents a major feature area with its own pages, components, and API calls:

| Module | Path | Description |
|--------|------|-------------|
| `dashboard` | `/dashboard` | Main dashboard with notifications, tasks, weather |
| `my-portfolio` | `/my-portfolio` | User's portfolio overview and performance |
| `reports` | `/reports` | PowerBI embedded reports |
| `due-diligence` | `/due-diligence` | Document management, AI parsing, chatbot |
| `operations-and-maintenance` | `/operations-and-maintenance` | O&M tracking, alerts, device status |
| `asset-management` | `/asset-management` | Asset lifecycle, devices, specifications |
| `security` | `/security` | Camera monitoring (Rombus integration) |
| `settings` | `/settings` | Users, companies, sites, roles, audit logs, connections |

### Layout Components (`src/components/layout/`)

| Component | Purpose |
|-----------|---------|
| `AuthLayout/` | Unauthenticated pages wrapper (login, reset password) |
| `BaseLayout/` | Authenticated pages with sidebar and header |
| `PageHeader/` | Top navigation bar with user menu, theme toggle |
| `PageSidebar/` | Left navigation menu with module links |
| `Breadcrumbs/` | Dynamic breadcrumb navigation |
| `NavMenu/` | Navigation menu items |
| `CompanyLogo/` | Company branding component |
| `CustomError/` | Error boundary and error pages |
| `ErrorLayout/` | Error page layout wrapper |
| `Main/` | Main content container |

### Common Components (`src/components/common/`)

| Component | Purpose |
|-----------|---------|
| `tables/BaseTable` | AG Grid base table with standard features |
| `tables/EditTable` | Editable AG Grid table variant |
| `tables/SitesTable` | Sites-specific table with custom columns |
| `tables/components/` | Table subcomponents (ColumnsModal, SearchAndActions) |
| `LoadingComponent/` | Loading spinners and skeletons |
| `FullPageLoader/` | Full page loading overlay |
| `FormattedNumericInput/` | Formatted number inputs |
| `FormattedIntegerNumericInput/` | Integer-only formatted inputs |
| `DocumentModal/` | Document viewer modal |
| `DocumentList/` | Document list with actions |
| `WeatherIndicator/` | Weather display component |
| `PowerProductionIndicator/` | Power production charts |
| `EfficiencyRateBar/` | Efficiency rate visualization |
| `SiteConditions/` | Site conditions display |
| `UploadButton/` | File upload button |
| `ToogleGroup/` | Toggle button group |
| `BootstrapTooltip/` | Styled tooltip |
| `DocImageRenderer/` | Document image rendering |
| `FieldDiscovery/` | AI field discovery component |

### React Contexts (`src/contexts/`)

| Context | File | Purpose |
|---------|------|---------|
| `AuthContext` | `auth/auth.tsx` | User authentication state, login/logout |
| `ThemeModeContext` | `theme/theme.tsx` | Light/dark theme toggle with localStorage |
| `NotificationsContext` | `notifications/` | Toast notification system |
| `ActionProcessorContext` | `action-processor/` | Async action queue handling |

### Custom Hooks (`src/hooks/`)

| Directory | Purpose |
|-----------|---------|
| `access/` | Permission and access control hooks |
| `common/` | Shared utility hooks |
| `login/` | Authentication hooks |
| `reset/` | Password reset hooks |
| `reset-request/` | Password reset request hooks |
| `settings/` | Settings management hooks |

### API Client (`src/api/`)

| File | Purpose | Key Functions |
|------|---------|---------------|
| `http-client.ts` | Axios instance with interceptors | Base HTTP client |
| `token-manager.ts` | JWT token storage/refresh | `getToken`, `setToken`, `clearToken` |
| `index.ts` | API base URL configuration | `API_BASE_URL` |
| `asset-management.ts` | Asset CRUD operations | Companies, sites, devices |
| `due-diligence.ts` | Document management | Documents, files, parsing |
| `operations-and-maintenance.ts` | O&M APIs | Alerts, status, cameras |
| `task-management.ts` | Task/board APIs | Boards, tasks, attachments |
| `user.ts` | User management | Users, roles, invitations |
| `dashboard.ts` | Dashboard data | Tasks, notifications |
| `reports.ts` | PowerBI integration | Report configs, embed tokens |
| `companies.ts` | Company APIs | Company CRUD |
| `connections.ts` | DAS connections | Connection management |
| `investor-dashboard.ts` | Investor APIs | Investor-specific views |
| `audit-log.ts` | Audit logging | Audit trail queries |
| `breadcrumbs.ts` | Navigation | Breadcrumb data |
| `security.ts` | Security APIs | Camera integration |
| `settings.ts` | Settings APIs | Configuration |
| `password-recovery.ts` | Password reset | Reset flow |
| `my-company.ts` | Current company | Company context |

### Theme System (`src/utils/styles/theme.ts`)

```typescript
// Theme factory function
getTheme(mode: 'light' | 'dark'): Theme

// Features:
// - Light and dark mode support
// - MUI component overrides
// - Custom color palette
// - Typography settings
// - localStorage persistence
// - System preference detection
```

---

## Backend Architecture

### Service Overview

| Service | Port | Purpose |
|---------|------|---------|
| `ilios-server` | 8000 | Main API server (FastAPI) |
| `ilios-DocAI` | - | Document AI processing (Cloud Functions) |
| `ilios-services` | - | Shared utilities |
| `rea-telemetry` | - | Telemetry data processing |

### Router Organization (`app/routers/`)

All routers registered in `app/main.py`:

#### Authentication & Account
| Router | Prefix | Purpose |
|--------|--------|---------|
| `auth_router` | `/api/auth` | Login, logout, token refresh |
| `account_router` | `/api/users/account` | Current user profile |
| `dashboard_tasks_router` | `/api/account/dashboard` | Dashboard tasks |
| `dashboard_notifications_router` | `/api/account/dashboard/notifications` | User notifications |

#### Investor Dashboard
| Router | Prefix | Purpose |
|--------|--------|---------|
| `investor_companies_router` | `/api/investor-dashboard/companies` | Investor company views |
| `investor_sites_router` | `/api/investor-dashboard/sites` | Investor site views |

#### Asset Management
| Router | Prefix | Purpose |
|--------|--------|---------|
| `companies_router` | `/api/companies` | Company CRUD |
| `sites_router` | `/api/sites` | Site CRUD |
| `devices_router` | `/api/sites/{site_id}/devices` | Device management |
| `device_documents_router` | `/api/sites/{site_id}/devices/{device_id}/documents` | Device documents |

#### Operations & Maintenance
| Router | Prefix | Purpose |
|--------|--------|---------|
| `alerts_router` | `/api/operations-and-maintenance/alerts` | Alert management |
| `om_companies_router` | `/api/operations-and-maintenance/companies` | O&M company views |
| `om_sites_router` | `/api/operations-and-maintenance/sites` | O&M site views |
| `om_site_cameras_router` | `/api/operations-and-maintenance/sites/{site_id}/cameras` | Site cameras |

#### Settings
| Router | Prefix | Purpose |
|--------|--------|---------|
| `audit_log_router` | `/api/settings/audit-logs` | Audit trail |
| `contractors_router` | `/api/contractors` | Contractor management |
| `settings_connections_router` | `/api/contractors/{company_id}/connections` | DAS connections |
| `my_company_router` | `/api/my-company` | Current company |
| `roles_router` | `/api/roles` | Role management |
| `settings_sites_router` | `/api/settings/sites` | Site settings |
| `users_router` | `/api/users` | User management |

#### Due Diligence
| Router | Prefix | Purpose |
|--------|--------|---------|
| `documents_router` | `/api/due-diligence/{site_id}/documents` | Document CRUD |
| `agreements_router` | `/api/due-diligence/{site_id}/agreements` | Agreement documents |
| `co_terminus_router` | `/api/due-diligence/{site_id}/co-terminus` | Co-terminus checks |
| `files_router` | `/api/due-diligence/{site_id}/documents/{document_id}/files` | File management |
| `files_parsing_router` | `/api/due-diligence/{site_id}/documents/{document_id}/files/{file_id}` | AI file parsing |
| `chatbot_router` | `/api/due-diligence/chatbot/{site_id}` | Document chatbot |

#### Task Tracker
| Router | Prefix | Purpose |
|--------|--------|---------|
| `board_router` | `/api/task-tracker/boards` | Kanban boards |
| `board_statuses_router` | `/api/task-tracker/boards/{board_id}/statuses` | Board statuses |
| `tasks_router` | `/api/task-tracker/boards/{board_id}/tasks` | Task CRUD |
| `attachments_router` | `/api/task-tracker/boards/{board_id}/tasks/{task_id}/attachments` | Task attachments |
| `site_visits_router` | `/api/task-tracker/boards/{board_id}/tasks/{task_id}/site-visits` | Site visits |
| `sv_uploads_router` | `/api/task-tracker/boards/{board_id}/tasks/{task_id}/site-visits` | Visit uploads |

#### Other
| Router | Prefix | Purpose |
|--------|--------|---------|
| `comments_router` | `/api/comments` | Entity comments |
| `cameras_router` | `/api/security/cameras` | Rombus cameras |
| `telemetry_router` | `/api/telemetry` | Device telemetry |
| `reports_companies_router` | `/api/reporting/companies` | Report companies |
| `reports_sites_router` | `/api/reporting/companies/{company_id}/sites` | Report sites |
| `reports_router` | `/api/reporting/reports` | PowerBI reports |
| `breadcrumbs_router` | `/api/breadcrumbs` | Navigation data |

#### Internal APIs
| Router | Prefix | Purpose |
|--------|--------|---------|
| `health_router` | `/health` | Health checks |
| `internal_router` | `/api/internal` | Internal operations |
| `internal_ai_router` | `/api/internal` | AI operations |
| `internal_telemetry_router` | `/api/internal` | Telemetry sync |
| `internal_sites_router` | `/api/internal` | Internal site ops |

### Models (`app/models/`)

Complete list of ORM models:

| Model | File | Description | Key Fields |
|-------|------|-------------|------------|
| `User` | `user.py` | User accounts | email, hashed_password, role_id, company_id |
| `Company` | `company.py` | Client companies | name, description, logo_url |
| `Site` | `site.py` | Physical locations | name, company_id, location, capacity |
| `Device` | `device.py` | Equipment/assets | site_id, device_type, manufacturer, specs |
| `Document` | `document.py` | DD documents | site_id, file_path, document_type, parsed_data |
| `File` | `file.py` | Uploaded files | document_id, storage_path, mime_type |
| `Task` | `task.py` | Task items | board_id, title, status_id, assignee_id |
| `Board` | `board.py` | Kanban boards | name, site_id, statuses |
| `Role` | `role.py` | User roles | name, permissions (JSON) |
| `Notification` | `notification.py` | User notifications | user_id, type, message, read |
| `Comment` | `comment.py` | Entity comments | entity_type, entity_id, user_id, content |
| `Alert` | `alert.py` | System alerts | site_id, severity, message, resolved |
| `Attachment` | `attachment.py` | Task attachments | task_id, file_path |
| `AuditLog` | `audit_log.py` | Audit trail | user_id, action, entity, timestamp |
| `Session` | `session.py` | User sessions | user_id, token, expires_at |
| `SiteVisit` | `site_visit.py` | Site visits | task_id, visit_date, notes |
| `SvUploads` | `sv_uploads.py` | Visit photos | site_visit_id, file_path |
| `DeviceDocument` | `device_document.py` | Device docs | device_id, document_type |
| `Telemetry` | `telemetry.py` | Telemetry mappings | site_id, external_id |
| `Chatbot` | `chatbot.py` | Chatbot sessions | site_id, session_token |
| `InternalConfiguration` | `internal_configuration.py` | App config | key, value |

### CRUD Layer (`app/crud/`)

Base CRUD class (`base_crud.py`) provides:
```python
class CRUDBase:
    def get(db, id) -> Model
    def get_multi(db, skip, limit, filters) -> List[Model]
    def create(db, obj_in) -> Model
    def update(db, db_obj, obj_in) -> Model
    def remove(db, id) -> Model
```

Specialized CRUD classes extend with domain logic:
- `company.py` - Company with site counts
- `site.py` - Site with device/document aggregations
- `user.py` - User with role/company joins
- `task.py` - Task with board/assignee relations
- `board_related_entity.py` - Board entity relationships
- `commented_entity.py` - Commentable entities

### Helpers (`app/helpers/`)

| Helper | Purpose |
|--------|---------|
| `authentication.py` | JWT token generation/validation |
| `authorization/` | Permission checking, role-based access |
| `powerbi.py` | PowerBI embed token generation |
| `email.py` | Mailgun email sending |
| `device_helper.py` | Device business logic |
| `notification_helper.py` | Notification creation/dispatch |
| `company_helper.py` | Company operations |
| `user_helper.py` | User operations |
| `invitations_handler.py` | User invitation flow |
| `password_recovery_handler.py` | Password reset flow |
| `due_diligence/` | Document processing logic |
| `files/` | File upload/download (GCS) |
| `security/` | Rombus camera integration |
| `telemetry/` | Device telemetry data |
| `task_tracker/` | Task management logic |
| `assets_management/` | Asset operations |
| `chatbot/` | Chatbot session management |
| `bq_data_sync_helper.py` | BigQuery data synchronization |
| `cloud_function_client.py` | GCP Cloud Function calls |
| `default_roles_helper.py` | Default role setup |
| `initial_setup_helper.py` | App initialization |

### Settings (`app/settings.py`)

Environment variable categories:

```python
# Framework
app_title, app_description

# Security
secret_key, api_key, access_token_expire_minutes

# Database (supports both custom and Replit vars)
db_host, db_user, db_password, db_name
PGHOST, PGUSER, PGPASSWORD, PGDATABASE, DATABASE_URL

# Email (Mailgun)
mailgun_rest_api_endpoint, mailgun_api_key, mailgun_domain_name

# Cloud Storage (GCS)
due_diligence_gcs_bucket, task_attachments_gcs_bucket
device_documents_gcs_bucket, sv_uploads_gcs_bucket

# AI Integration
file_parse_function_url, co_terminus_function_url
chatbot_*_function_url, ml_api_key

# Telemetry
telemetry_token_function_url, telemetry_*_function_url

# PowerBI
pbi_tenant_id, pbi_client_id, pbi_client_secret
pbi_workspace_id (dev: 59754A20-0A6A-4EA8-BD10-B37171F8FF51)

# Redis
redis_url (Upstash with TLS)
```

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Company   │──┬──│    Site     │──┬──│   Device    │
└─────────────┘  │  └─────────────┘  │  └─────────────┘
                 │         │         │         │
                 │         │         │         ▼
                 │         │         │  ┌─────────────────┐
                 │         │         └──│ DeviceDocument  │
                 │         │            └─────────────────┘
                 │         │
                 │         ├──────────┬──────────┬──────────┐
                 │         │          │          │          │
                 │         ▼          ▼          ▼          ▼
                 │  ┌───────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
                 │  │  Document │ │ Board  │ │ Alert  │ │Telemetry │
                 │  └───────────┘ └────────┘ └────────┘ └──────────┘
                 │         │          │
                 │         ▼          ▼
                 │  ┌───────────┐ ┌────────┐
                 │  │   File    │ │  Task  │──┬──────────┐
                 │  └───────────┘ └────────┘  │          │
                 │                    │       ▼          ▼
                 │                    │ ┌───────────┐ ┌────────────┐
                 │                    │ │Attachment │ │ SiteVisit  │
                 │                    │ └───────────┘ └────────────┘
                 │                    │                    │
                 │                    │                    ▼
                 │                    │              ┌───────────┐
                 │                    │              │ SvUploads │
                 │                    │              └───────────┘
                 │                    │
                 ▼                    ▼
          ┌───────────┐        ┌───────────┐
          │   User    │◄───────│  Assignee │
          └───────────┘        └───────────┘
                │
                ▼
          ┌───────────┐     ┌───────────────┐
          │   Role    │     │ Notification  │
          └───────────┘     └───────────────┘
```

### Table Details

#### Core Business Tables

**users**
```sql
id              SERIAL PRIMARY KEY
email           VARCHAR UNIQUE NOT NULL
hashed_password VARCHAR NOT NULL
first_name      VARCHAR
last_name       VARCHAR
phone           VARCHAR
role_id         INTEGER REFERENCES roles(id)
company_id      INTEGER REFERENCES companies(id)
is_active       BOOLEAN DEFAULT true
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

**companies**
```sql
id              SERIAL PRIMARY KEY
name            VARCHAR NOT NULL
description     TEXT
logo_url        VARCHAR
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

**sites**
```sql
id              SERIAL PRIMARY KEY
name            VARCHAR NOT NULL
company_id      INTEGER REFERENCES companies(id)
address         VARCHAR
city            VARCHAR
state           VARCHAR
country         VARCHAR
latitude        DECIMAL
longitude       DECIMAL
capacity_mw     DECIMAL
site_type       VARCHAR
status          VARCHAR
created_at      TIMESTAMP
updated_at      TIMESTAMP
-- Plus many additional fields for site metadata
```

**devices**
```sql
id              SERIAL PRIMARY KEY
site_id         INTEGER REFERENCES sites(id)
name            VARCHAR
device_type     VARCHAR
manufacturer    VARCHAR
model           VARCHAR
serial_number   VARCHAR
installation_date DATE
specifications  JSONB
status          VARCHAR
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

#### Document Management

**documents**
```sql
id              SERIAL PRIMARY KEY
site_id         INTEGER REFERENCES sites(id)
name            VARCHAR
document_type   VARCHAR
section         VARCHAR
status          VARCHAR
parsed_data     JSONB
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

**files**
```sql
id              SERIAL PRIMARY KEY
document_id     INTEGER REFERENCES documents(id)
original_name   VARCHAR
storage_path    VARCHAR
mime_type       VARCHAR
file_size       INTEGER
parsing_status  VARCHAR
parsed_data     JSONB
created_at      TIMESTAMP
```

#### Task Management

**boards**
```sql
id              SERIAL PRIMARY KEY
name            VARCHAR NOT NULL
site_id         INTEGER REFERENCES sites(id)
created_by      INTEGER REFERENCES users(id)
created_at      TIMESTAMP
```

**tasks**
```sql
id              SERIAL PRIMARY KEY
board_id        INTEGER REFERENCES boards(id)
title           VARCHAR NOT NULL
description     TEXT
status_id       INTEGER REFERENCES board_statuses(id)
assignee_id     INTEGER REFERENCES users(id)
due_date        DATE
priority        VARCHAR
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

#### Supporting Tables

**roles**
```sql
id              SERIAL PRIMARY KEY
name            VARCHAR UNIQUE NOT NULL
permissions     JSONB
is_system       BOOLEAN DEFAULT false
created_at      TIMESTAMP
```

**notifications**
```sql
id              SERIAL PRIMARY KEY
user_id         INTEGER REFERENCES users(id)
type            VARCHAR
title           VARCHAR
message         TEXT
is_read         BOOLEAN DEFAULT false
entity_type     VARCHAR
entity_id       INTEGER
created_at      TIMESTAMP
```

**comments**
```sql
id              SERIAL PRIMARY KEY
entity_type     VARCHAR NOT NULL
entity_id       INTEGER NOT NULL
user_id         INTEGER REFERENCES users(id)
content         TEXT NOT NULL
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

**alerts**
```sql
id              SERIAL PRIMARY KEY
site_id         INTEGER REFERENCES sites(id)
device_id       INTEGER REFERENCES devices(id)
severity        VARCHAR
category        VARCHAR
message         TEXT
is_resolved     BOOLEAN DEFAULT false
resolved_at     TIMESTAMP
created_at      TIMESTAMP
```

**audit_log**
```sql
id              SERIAL PRIMARY KEY
user_id         INTEGER REFERENCES users(id)
action          VARCHAR NOT NULL
entity_type     VARCHAR
entity_id       INTEGER
old_values      JSONB
new_values      JSONB
ip_address      VARCHAR
created_at      TIMESTAMP
```

---

## API Routes (Complete)

### Authentication (`/api/auth`)
```
POST /api/auth/login              # User login, returns tokens
POST /api/auth/logout             # Invalidate session
POST /api/auth/refresh            # Refresh access token
POST /api/auth/password/reset     # Request password reset
POST /api/auth/password/confirm   # Confirm password reset
```

### Account (`/api/users/account`)
```
GET  /api/users/account/me        # Current user profile
PUT  /api/users/account/me        # Update profile
```

### Dashboard (`/api/account/dashboard`)
```
GET  /api/account/dashboard/tasks            # Dashboard tasks
GET  /api/account/dashboard/notifications    # User notifications
PUT  /api/account/dashboard/notifications/{id}/read  # Mark read
```

### Investor Dashboard (`/api/investor-dashboard`)
```
GET  /api/investor-dashboard/companies       # Investor companies
GET  /api/investor-dashboard/companies/{id}  # Company details
GET  /api/investor-dashboard/sites           # Investor sites
GET  /api/investor-dashboard/sites/{id}      # Site details
```

### Companies (`/api/companies`)
```
GET    /api/companies                        # List companies
POST   /api/companies                        # Create company
GET    /api/companies/{id}                   # Get company
PUT    /api/companies/{id}                   # Update company
DELETE /api/companies/{id}                   # Delete company
GET    /api/companies/{id}/sites             # Company sites
```

### Sites (`/api/sites`)
```
GET    /api/sites                            # List sites
POST   /api/sites                            # Create site
GET    /api/sites/{id}                       # Get site
PUT    /api/sites/{id}                       # Update site
DELETE /api/sites/{id}                       # Delete site
```

### Devices (`/api/sites/{site_id}/devices`)
```
GET    /api/sites/{site_id}/devices          # List devices
POST   /api/sites/{site_id}/devices          # Create device
GET    /api/sites/{site_id}/devices/{id}     # Get device
PUT    /api/sites/{site_id}/devices/{id}     # Update device
DELETE /api/sites/{site_id}/devices/{id}     # Delete device
```

### Due Diligence Documents (`/api/due-diligence/{site_id}/documents`)
```
GET    /api/due-diligence/{site_id}/documents         # List documents
POST   /api/due-diligence/{site_id}/documents         # Create document
GET    /api/due-diligence/{site_id}/documents/{id}    # Get document
PUT    /api/due-diligence/{site_id}/documents/{id}    # Update document
DELETE /api/due-diligence/{site_id}/documents/{id}    # Delete document
```

### Files (`/api/due-diligence/{site_id}/documents/{document_id}/files`)
```
GET    /api/due-diligence/{site_id}/documents/{document_id}/files          # List files
POST   /api/due-diligence/{site_id}/documents/{document_id}/files          # Upload file
GET    /api/due-diligence/{site_id}/documents/{document_id}/files/{id}     # Get file
DELETE /api/due-diligence/{site_id}/documents/{document_id}/files/{id}     # Delete file
GET    /api/due-diligence/{site_id}/documents/{document_id}/files/{id}/download  # Download
```

### Files Parsing (`/api/due-diligence/{site_id}/documents/{document_id}/files/{file_id}`)
```
POST   /api/due-diligence/{site_id}/documents/{document_id}/files/{file_id}/parse        # Trigger AI parsing
GET    /api/due-diligence/{site_id}/documents/{document_id}/files/{file_id}/parse/status # Parsing status
```

### Agreements (`/api/due-diligence/{site_id}/agreements`)
```
GET    /api/due-diligence/{site_id}/agreements          # List agreements
POST   /api/due-diligence/{site_id}/agreements          # Create agreement
GET    /api/due-diligence/{site_id}/agreements/{id}     # Get agreement
PUT    /api/due-diligence/{site_id}/agreements/{id}     # Update agreement
DELETE /api/due-diligence/{site_id}/agreements/{id}     # Delete agreement
```

### Co-Terminus (`/api/due-diligence/{site_id}/co-terminus`)
```
GET    /api/due-diligence/{site_id}/co-terminus         # Get co-terminus check
POST   /api/due-diligence/{site_id}/co-terminus         # Trigger co-terminus analysis
```

### Chatbot (`/api/due-diligence/chatbot/{site_id}`)
```
POST   /api/due-diligence/chatbot/{site_id}/session   # Start session
POST   /api/due-diligence/chatbot/{site_id}/message   # Send message
GET    /api/due-diligence/chatbot/{site_id}/history   # Chat history
```

### Task Tracker Boards (`/api/task-tracker/boards`)
```
GET    /api/task-tracker/boards                       # List boards
POST   /api/task-tracker/boards                       # Create board
GET    /api/task-tracker/boards/{board_id}            # Get board
PUT    /api/task-tracker/boards/{board_id}            # Update board
DELETE /api/task-tracker/boards/{board_id}            # Delete board
```

### Board Statuses (`/api/task-tracker/boards/{board_id}/statuses`)
```
GET    /api/task-tracker/boards/{board_id}/statuses          # List statuses
POST   /api/task-tracker/boards/{board_id}/statuses          # Create status
PUT    /api/task-tracker/boards/{board_id}/statuses/{id}     # Update status
DELETE /api/task-tracker/boards/{board_id}/statuses/{id}     # Delete status
```

### Tasks (`/api/task-tracker/boards/{board_id}/tasks`)
```
GET    /api/task-tracker/boards/{board_id}/tasks             # List tasks
POST   /api/task-tracker/boards/{board_id}/tasks             # Create task
GET    /api/task-tracker/boards/{board_id}/tasks/{task_id}   # Get task
PUT    /api/task-tracker/boards/{board_id}/tasks/{task_id}   # Update task
DELETE /api/task-tracker/boards/{board_id}/tasks/{task_id}   # Delete task
```

### Task Attachments (`/api/task-tracker/boards/{board_id}/tasks/{task_id}/attachments`)
```
GET    /api/task-tracker/boards/{board_id}/tasks/{task_id}/attachments          # List attachments
POST   /api/task-tracker/boards/{board_id}/tasks/{task_id}/attachments          # Add attachment
GET    /api/task-tracker/boards/{board_id}/tasks/{task_id}/attachments/{id}     # Get attachment
DELETE /api/task-tracker/boards/{board_id}/tasks/{task_id}/attachments/{id}     # Remove attachment
```

### Site Visits (`/api/task-tracker/boards/{board_id}/tasks/{task_id}/site-visits`)
```
GET    /api/task-tracker/boards/{board_id}/tasks/{task_id}/site-visits          # List visits
POST   /api/task-tracker/boards/{board_id}/tasks/{task_id}/site-visits          # Create visit
GET    /api/task-tracker/boards/{board_id}/tasks/{task_id}/site-visits/{id}     # Get visit
PUT    /api/task-tracker/boards/{board_id}/tasks/{task_id}/site-visits/{id}     # Update visit
DELETE /api/task-tracker/boards/{board_id}/tasks/{task_id}/site-visits/{id}     # Delete visit
```

### Site Visit Uploads (`/api/task-tracker/boards/{board_id}/tasks/{task_id}/site-visits`)
```
POST   /api/task-tracker/boards/{board_id}/tasks/{task_id}/site-visits/{visit_id}/uploads     # Upload photo
GET    /api/task-tracker/boards/{board_id}/tasks/{task_id}/site-visits/{visit_id}/uploads     # List uploads
DELETE /api/task-tracker/boards/{board_id}/tasks/{task_id}/site-visits/{visit_id}/uploads/{id}  # Delete upload
```

### Operations & Maintenance (`/api/operations-and-maintenance`)
```
GET  /api/operations-and-maintenance/alerts           # List alerts
GET  /api/operations-and-maintenance/alerts/{id}      # Get alert
PUT  /api/operations-and-maintenance/alerts/{id}      # Update alert

GET  /api/operations-and-maintenance/companies        # O&M companies
GET  /api/operations-and-maintenance/companies/{id}   # Company details

GET  /api/operations-and-maintenance/sites            # O&M sites
GET  /api/operations-and-maintenance/sites/{id}       # Site details

GET  /api/operations-and-maintenance/sites/{id}/cameras  # Site cameras
```

### Security (`/api/security`)
```
GET  /api/security/cameras                            # List cameras
GET  /api/security/cameras/{id}                       # Camera details
GET  /api/security/cameras/{id}/stream                # Stream URL
```

### Reports (`/api/reporting`)
```
GET  /api/reporting/companies                         # Report companies
GET  /api/reporting/companies/{id}/sites              # Report sites
GET  /api/reporting/reports                           # PowerBI reports
GET  /api/reporting/reports/{id}/embed               # Embed config
```

### Users (`/api/users`)
```
GET    /api/users                                     # List users
POST   /api/users                                     # Create user
GET    /api/users/{id}                                # Get user
PUT    /api/users/{id}                                # Update user
DELETE /api/users/{id}                                # Delete user
POST   /api/users/invite                              # Send invitation
```

### Roles (`/api/roles`)
```
GET    /api/roles                                     # List roles
POST   /api/roles                                     # Create role
GET    /api/roles/{id}                                # Get role
PUT    /api/roles/{id}                                # Update role
DELETE /api/roles/{id}                                # Delete role
```

### Audit Logs (`/api/settings/audit-logs`)
```
GET    /api/settings/audit-logs                       # List audit logs (with filters)
GET    /api/settings/audit-logs/{id}                  # Get audit log entry
```

### Settings Sites (`/api/settings/sites`)
```
GET    /api/settings/sites                            # List sites for settings
GET    /api/settings/sites/{id}                       # Get site settings
PUT    /api/settings/sites/{id}                       # Update site settings
```

### Contractors (`/api/contractors`)
```
GET    /api/contractors                               # List contractors
POST   /api/contractors                               # Create contractor
GET    /api/contractors/{id}                          # Get contractor
PUT    /api/contractors/{id}                          # Update contractor
DELETE /api/contractors/{id}                          # Delete contractor
```

### Connections (`/api/contractors/{company_id}/connections`)
```
GET    /api/contractors/{company_id}/connections              # List DAS connections
POST   /api/contractors/{company_id}/connections              # Create connection
GET    /api/contractors/{company_id}/connections/{id}         # Get connection
PUT    /api/contractors/{company_id}/connections/{id}         # Update connection
DELETE /api/contractors/{company_id}/connections/{id}         # Delete connection
POST   /api/contractors/{company_id}/connections/{id}/test    # Test connection
```

### My Company (`/api/my-company`)
```
GET    /api/my-company                                # Get current user's company
PUT    /api/my-company                                # Update company
GET    /api/my-company/users                          # List company users
```

### Breadcrumbs (`/api/breadcrumbs`)
```
GET    /api/breadcrumbs/{entity_type}/{entity_id}     # Get breadcrumb path
```

### Comments (`/api/comments`)
```
GET    /api/comments?entity_type=X&entity_id=Y       # Get comments
POST   /api/comments                                  # Create comment
PUT    /api/comments/{id}                             # Update comment
DELETE /api/comments/{id}                             # Delete comment
```

### Telemetry (`/api/telemetry`)
```
GET  /api/telemetry/sites/{site_id}                   # Site telemetry
GET  /api/telemetry/devices/{device_id}               # Device telemetry
```

### Device Documents (`/api/sites/{site_id}/devices/{device_id}/documents`)
```
GET    /api/sites/{site_id}/devices/{device_id}/documents          # List device documents
POST   /api/sites/{site_id}/devices/{device_id}/documents          # Add document
GET    /api/sites/{site_id}/devices/{device_id}/documents/{id}     # Get document
DELETE /api/sites/{site_id}/devices/{device_id}/documents/{id}     # Remove document
```

### Health (`/health`)
```
GET    /health                                        # Basic health check
```

### Internal APIs (`/api/internal`) - internal_router
```
GET    /api/internal/comments                         # List internal comments
POST   /api/internal/comments                         # Create internal comment
GET    /api/internal/devices                          # List devices (internal)
GET    /api/internal/devices/{id}                     # Get device (internal)
GET    /api/internal/documents                        # List documents (internal)
GET    /api/internal/documents/{id}                   # Get document (internal)
```

### Internal AI (`/api/internal`) - internal_ai_router
```
GET    /api/internal/configs                          # Get AI configurations
PUT    /api/internal/configs                          # Update AI configurations
GET    /api/internal/files/{file_id}/status           # Get file parsing status
POST   /api/internal/files/{file_id}/callback         # AI parsing callback
GET    /api/internal/co-terminus/{site_id}/status     # Co-terminus check status
POST   /api/internal/co-terminus/{site_id}/callback   # Co-terminus callback
```

### Internal Telemetry (`/api/internal`) - internal_telemetry_router
```
GET    /api/internal/alerts                           # Get telemetry alerts
POST   /api/internal/alerts                           # Create telemetry alert
PUT    /api/internal/alerts/{id}                      # Update alert
GET    /api/internal/telemetry/devices                # Get telemetry device mappings
POST   /api/internal/telemetry/devices                # Create device mapping
PUT    /api/internal/telemetry/devices/{id}           # Update device mapping
GET    /api/internal/redis/health                     # Redis health check
POST   /api/internal/redis/flush                      # Flush Redis cache
```

### Internal Sites (`/api/internal`) - internal_sites_router
```
GET    /api/internal/sites/{site_id}/weather          # Get site weather
PUT    /api/internal/sites/{site_id}/weather          # Update site weather data
```

### Health (`/health`) - health_router
```
GET    /health                                        # Basic application health check
```

---

## Third-Party Integrations

### PostgreSQL (Replit Built-in)
- **Status:** Working
- **Connection:** `DATABASE_URL` environment variable
- **ORM:** SQLAlchemy 2.0 with Alembic migrations
- **Notes:** Neon-backed, supports rollback

### Redis (Upstash)
- **Status:** Working
- **Connection:** `REDIS_URL` (TLS required: `rediss://`)
- **Usage:** Session caching, rate limiting
- **Health:** `/api/internal/health`
- **Tip:** When copying Upstash URLs, paste to text editor first to verify completeness

### PowerBI
- **Status:** Working
- **Credentials:**
  - `pbi_tenant_id` - Azure AD tenant
  - `pbi_client_id` - App registration client ID
  - `pbi_client_secret` - App secret (stored as `pbi_client_secret`)
- **Workspace ID:** `59754A20-0A6A-4EA8-BD10-B37171F8FF51` (dev)
- **Helper:** `app/helpers/powerbi.py`
- **Embed flow:** Get token → Embed in iframe

### Mailgun
- **Status:** Configured
- **Region:** US (api.mailgun.net)
- **Domain:** iliospower.com
- **API Key:** `mailgun_api_key` secret
- **Helper:** `app/helpers/email.py`
- **Templates:** Password reset, invitations

### Rombus (Security Cameras)
- **Status:** Configured
- **API Key:** `rombus_api_key` secret
- **Helper:** `app/helpers/security/`
- **Features:** Camera list, live streams, recordings

### AG Grid Enterprise
- **Status:** Licensed
- **License Key:** `REACT_APP_AG_GRID_LICENSE_KEY` secret
- **Version:** 31.1.1
- **Note:** Must use `reactiveCustomComponents={true}` for React components

### Google Cloud Storage (GCS)
- **Status:** Configured
- **Authentication:** Service account key file (`key.json` or `service_account_key_file_path`)
- **Buckets:**
  | Bucket | Setting | Purpose |
  |--------|---------|---------|
  | `due-diligence-files` | `due_diligence_gcs_bucket` | Due diligence document storage |
  | `dev-task-tracker-attachments` | `task_attachments_gcs_bucket` | Task file attachments |
  | `dev-device-documents` | `device_documents_gcs_bucket` | Device documentation |
  | `dev-site-visit-uploads` | `sv_uploads_gcs_bucket` | Site visit photos |
- **File Operations:**
  - Upload: `app/helpers/files/` handles multipart uploads
  - Download: Generates signed URLs (expiry: `file_download_link_expiration_minutes`)
  - Allowed extensions: `allowed_extensions` (pdf, docx, jpeg, jpg, png)
  - Max file size: `allowed_filesize` (default 100MB)
- **Helper Files:**
  - `app/helpers/files/gcs_helper.py` - GCS upload/download operations
  - `app/helpers/files/file_validator.py` - File validation

### BigQuery
- **Status:** Configured
- **Project:** `gcp_project_id` setting
- **Usage:**
  - Site and device data synchronization
  - Analytics and reporting data warehouse
  - Telemetry data aggregation
- **Helper:** `app/helpers/bq_data_sync_helper.py`
- **Key Functions:**
  - Data sync from PostgreSQL to BigQuery
  - Telemetry data import
  - Report data preparation
- **Trigger:** POST `/api/internal/sync/bigquery`
- **Related:** `app/bigquery/` directory for query definitions

### Google Cloud Functions
- **Status:** Configured
- **Authentication:** `ml_api_key` secret for API authentication
- **Functions:**
  | Setting | Purpose | Trigger |
  |---------|---------|---------|
  | `file_parse_function_url` | AI document parsing (OCR, field extraction) | POST with file data |
  | `co_terminus_function_url` | Co-terminus lease analysis | POST with document IDs |
  | `chatbot_upload_file_function_url` | Upload file to chatbot context | POST with file |
  | `chatbot_mark_actual_function_url` | Mark document as actual | POST |
  | `chatbot_delete_file_function_url` | Remove file from chatbot | POST |
  | `chatbot_session_token_function_url` | Get chatbot session token | POST |
  | `telemetry_token_function_url` | Get telemetry API token | POST |
  | `telemetry_sites_function_url` | Sync site telemetry data | GET/POST |
  | `telemetry_devices_function_url` | Sync device telemetry data | GET/POST |
  | `telemetry_device_static_info_func_url` | Get device static info | GET |
- **Helper:** `app/helpers/cloud_function_client.py` - HTTP client for function calls
- **Timeout:** `co_terminus_stuck_threshold` (default 15 min) for long-running operations

### Document AI (ilios-DocAI)
- **Status:** Separate service
- **API Key:** `ml_api_key` secret
- **Features:**
  - Document parsing (OCR, field extraction)
  - Chatbot with LLM
  - Vector embeddings (Vertex AI)
  - Classification and validation

---

## Authentication Flow

### Login Flow
```
1. User → POST /api/auth/login (email, password)
2. Backend validates credentials against hashed password
3. Backend generates JWT access token (60 min) + refresh token
4. Backend creates session in sessions table
5. Frontend stores tokens in localStorage via token-manager.ts
6. Frontend adds Authorization header via http-client.ts interceptor
```

### Token Refresh Flow
```
1. http-client.ts interceptor detects 401 response
2. Frontend calls POST /api/auth/refresh with refresh token
3. Backend validates refresh token and session
4. Backend returns new access token
5. Frontend retries original request
```

### Protected Route Flow (Frontend)
```
1. Route wrapped with withAuthControl HOC
2. AuthContext checks isAuthenticated
3. If false → Redirect to /login
4. If true → Check role permissions
5. If unauthorized → Show error or redirect
```

### Protected Endpoint Flow (Backend)
```python
@router.get("/protected")
async def protected_route(
    current_user: User = Depends(get_current_user)
):
    # get_current_user validates JWT and returns User
    # Raises 401 if invalid
    return {"user": current_user.email}
```

### Role-Based Access
- Roles stored in `roles` table with `permissions` JSONB field
- Permissions checked via `app/helpers/authorization/`
- Frontend uses `hooks/access/` for permission checks
- Backend uses dependency injection for route protection

---

## Key Files Reference

### Frontend Entry Points
| File | Purpose |
|------|---------|
| `src/index.tsx` | App bootstrap, providers |
| `src/App.tsx` | Router configuration (250+ lines) |
| `src/contexts/auth/auth.tsx` | Auth provider and context |
| `src/contexts/theme/theme.tsx` | Theme provider and context |
| `src/api/http-client.ts` | Axios instance with interceptors |
| `src/api/token-manager.ts` | JWT token management |
| `src/utils/styles/theme.ts` | MUI theme factory |

### Backend Entry Points
| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app factory, router registration |
| `app/settings.py` | Pydantic settings (196 lines) |
| `app/dependencies.py` | Dependency injection |
| `app/db/session.py` | Database session factory |
| `app/helpers/authentication.py` | JWT handling |
| `app/middlewares/` | Request logging, audit |

### Configuration
| File | Purpose |
|------|---------|
| `replit.md` | Project documentation |
| `ARCHITECTURE.md` | This file |
| `frontend/.../package.json` | Frontend dependencies |
| `backend/.../pyproject.toml` | Backend dependencies |
| `alembic.ini` | Migration config |
| `alembic/versions/` | Migration files |

---

## Development Workflows

### Start Development
```bash
# Frontend (Port 5000)
cd frontend/rea-investment-fe && PORT=5000 npm start

# Backend (Port 8000)
cd backend/ilios-server && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Test Credentials
- **Email:** system@user.com
- **Password:** SystemUser123!

### Database Migrations
```bash
cd backend/ilios-server

# Generate migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Adding New Features

#### New API Endpoint
1. Create Pydantic schema in `app/schema/`
2. Create/update CRUD in `app/crud/`
3. Add business logic helper in `app/helpers/`
4. Create router in `app/routers/`
5. Register router in `app/main.py`

#### New Frontend Module
1. Create module folder in `src/modules/`
2. Add routes in `src/App.tsx`
3. Create API functions in `src/api/`
4. Add navigation link in `PageSidebar`
5. Create page components

#### New Database Table
1. Create SQLAlchemy model in `app/models/`
2. Create migration: `alembic revision --autogenerate`
3. Apply migration: `alembic upgrade head`
4. Create CRUD class in `app/crud/`

### Theme Customization
- Edit `src/utils/styles/theme.ts`
- Modify `getTheme()` for light/dark variants
- Components use `theme.palette.*` for colors
- Toggle persists to localStorage

---

*Last updated: January 2026*

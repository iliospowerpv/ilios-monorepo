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
- **UI/UX Decisions**: Standardized "Projects" terminology, robust navigation (Entity Context, Module Sidebar, Breadcrumb), a unified Context Bar for scope management, a static Asset Management Overview with drag-and-drop features, a collapsible sidebar, and consolidated admin/settings modules for improved user experience and access control.
- **Data Room**: Hybrid PDF/document viewer with AI-extracted field linking, programmatic navigation, text search, highlighting, and an audit trail with a sequential verification workflow and bulk acceptance. Features a collapsible Project Summary Panel for cross-document analysis.

### Backend
- **Technology Stack**: Python 3.11, FastAPI, SQLAlchemy, Alembic, PostgreSQL.
- **Core Modules**: Workspace, Finance (capital governance, budgeting, vendor management), Acquisitions (13-stage deal pipeline), and Project Hub (unified asset management and due diligence).
- **Access Control**: Multi-Company Access System with granular authorization using a Canonical Effective-Access Resolver and Module-Level Permission Enforcement. Includes a Role Profiles System and a Portfolio Hub Boundary Model for data visibility.
- **Architectural Guardrails**: Asset Management Overview functions as a static record, linking to operational modules for live metrics.
- **Telemetry Module**: Project-scoped telemetry for Data Acquisition Systems (DAS) integration, health monitoring, and device mapping, including a demo data interceptor. Supports company-scoped DAS providers.
- **Document Versioning & Promotion**: Manages lender-quality Data Room document versions with a "Promote to Current Assumptions" workflow, supporting `candidate`, `active`, and `retired` `ProjectFact` states.
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

## External Dependencies
- **PostgreSQL**: Primary relational database.
- **Redis**: Used for caching and session management.
- **PowerBI**: Integrated for reporting and business intelligence.
- **Mailgun**: Configured for email services.
- **Rombus**: Integrated for camera/security functionalities.
- **AG Grid**: Enterprise license for advanced table functionalities.
- **OpenAI**: Utilized for in-app AI parsing capabilities.
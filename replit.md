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
- **UI/UX Decisions**: Standardized "Projects" terminology, robust navigation (Entity Context, Module Sidebar, Breadcrumb), a unified Context Bar for scope management, a static Asset Management Overview with drag-and-drop features, a collapsible sidebar, and consolidated admin/settings modules. Unified company landing page at `/project-hub/companies/:companyId` with Overview, Projects, Tasks, and Performance tabs.
- **Data Room**: Hybrid PDF/document viewer with AI-extracted field linking, programmatic navigation, text search, highlighting, audit trail, and a sequential verification workflow with bulk acceptance. Features a collapsible Project Summary Panel for cross-document analysis.

### Backend
- **Technology Stack**: Python 3.11, FastAPI, SQLAlchemy, Alembic, PostgreSQL.
- **Core Modules**: Workspace, Finance (capital governance, budgeting, vendor management), Acquisitions (13-stage deal pipeline), and Project Hub (unified asset management and due diligence).
- **Access Control**: Multi-Company Access System with granular authorization using a Canonical Effective-Access Resolver and Module-Level Permission Enforcement. Includes a Role Profiles System and a Portfolio Hub Boundary Model for data visibility.
- **Telemetry Module**: Project-scoped and company-scoped telemetry for Data Acquisition Systems (DAS) integration, health monitoring, and device mapping. Features a V2 architecture with a DB-backed provider catalog, pluggable `ProviderAdapter` abstraction, durable credential storage using GCP Secret Manager, and a three-state account model. Includes a demo telemetry system for simulated solar data.
- **Document Versioning & Promotion**: Manages lender-quality Data Room document versions with a "Promote to Current Assumptions" workflow, supporting `candidate`, `active`, and `retired` `ProjectFact` states.
- **Poison Pill Toggle**: Interactive flag on due diligence document keys allowing users to manually mark terms as poison pills, persisted via `is_poison_pill` and `poison_pill_notes`. User-set flags take precedence over AI-detected flags.
- **Extraction Registry & Prompt Studio**: Scalable system for dynamic document type and field configuration using database-driven schemas and prompt templates.
- **In-App AI Parsing**: Fully in-app document parsing using Replit AI Integrations (OpenAI), featuring an `InAppParsingService` for file handling, text extraction, LLM calls, observability, and retry logic. Implements idempotency and concurrency safety.
- **Storage Service Abstraction**: Replit-native storage architecture with an abstract `StorageService` interface, supporting `ReplitStorageService`, optional `GCSStorageService`, and `HybridStorageService`.
- **Data Room Acceptance Safety**: Enforces parse run history panel for files and validates `run_id` and run status before allowing bulk acceptance of extracted data.
- **Contacts System**: CRM-style contact management for tracking external people related to portfolio, company, and project entities.
- **Finance Integration & Data Ingestion**: Company-level, read-only integration supporting multiple external providers with a pluggable architecture. Encrypted credentials, role-based access, and normalized storage with upsert semantics.
- **Company & Site Creation**: Restricted company creation with structured address fields. Site creation requires `assets_management:edit` permission.
- **Entity Directory System**: Portfolio-scoped directory of legal/business entities with project-level and deal-level role assignments, including a dedicated Portfolio Admin page and a shared `EntityPicker` UI component.
- **Project Import Tool**: Bulk import projects from CSV/XLSX files via a multi-step wizard (Upload → Map Fields → Validate → Import) with auto-mapping, validation, and duplicate detection.
- **Archive & Restore (Soft-Delete)**: Companies and Projects/Sites support soft-delete via `is_archived` flags with cascade archiving.
- **Home Dashboard "Your Projects" Widget**: Extends `/api/workspace` with project data for displaying access-controlled project cards.
- **In-App Performance Report**: Fallback reporting for demo sites where PowerBI has no BigQuery data, generating daily/monthly performance data using the demo telemetry pipeline.

## External Dependencies
- **PostgreSQL**: Primary relational database.
- **Redis**: Used for caching and session management.
- **PowerBI**: Integrated for reporting and business intelligence.
- **Mailgun**: Configured for email services.
- **Rombus**: Integrated for camera/security functionalities.
- **AG Grid**: Enterprise license for advanced table functionalities.
- **OpenAI**: Utilized for in-app AI parsing capabilities.
- 
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

## External Dependencies
- **PostgreSQL**: Primary relational database.
- **Redis**: Used for caching and session management.
- **PowerBI**: Integrated for reporting and business intelligence.
- **Mailgun**: Configured for email services.
- **Rombus**: Integrated for camera/security functionalities.
- **AG Grid**: Enterprise license for advanced table functionalities.
# iliOS - REA Investment Platform

## Overview
iliOS is a real estate asset investment management platform designed to manage the entire lifecycle of real estate investments, from acquisition and due diligence to asset management, financial tracking, and reporting. The platform aims to enhance decision-making through data-driven insights and improve operational efficiency for real estate investors and asset managers. Key capabilities include secure user authentication, multi-company user membership, a user-centric workspace, comprehensive asset and task management, financial oversight with budgeting and vendor management, sales pipeline tracking, and robust reporting tools. iliOS serves as a centralized system for investment oversight and operational governance for real estate professionals, with a vision to become the leading platform for data-driven real estate investment.

## User Preferences
I prefer detailed explanations and thorough documentation for any implemented features or architectural decisions.
I expect iterative development, with clear communication before significant changes are made.
Do not change the fundamental "Site" entity in the backend; use "Project" only as a UI terminology update.

## System Architecture

### Frontend
- **Technology Stack**: React 18, TypeScript, Material UI (MUI), React Query, React Router DOM, AG Grid, Chart.js, Webpack 5.
- **UI/UX Decisions**: Standardized "Projects" terminology, robust navigation (Entity Context, Module Sidebar, Breadcrumb), a unified Context Bar for scope management, a static Asset Management Overview with drag-and-drop features, a collapsible sidebar, and consolidated admin/settings modules for improved user experience and access control.
- **Data Room Features**: Hybrid PDF/document viewer with programmatic page navigation, text search, and highlighting. Links AI-extracted fields to specific pages for evidence-based verification and provides an audit trail with a sequential verification workflow and bulk acceptance capabilities.
- **Project Summary Panel**: Collapsible panel within the Data Room providing cross-document analysis, including terms & values roll-up, co-terminus checks, and a project-level due diligence health indicator.

### Backend
- **Technology Stack**: Python 3.11, FastAPI, SQLAlchemy, Alembic, PostgreSQL.
- **Core Modules**: Workspace, Finance (capital governance, budgeting, vendor management), Acquisitions (13-stage deal pipeline), and Project Hub (unified asset management and due diligence).
- **Access Control**: Multi-Company Access System with granular authorization using a Canonical Effective-Access Resolver and Module-Level Permission Enforcement. Includes a Role Profiles System for detailed stakeholder definitions and a Portfolio Hub Boundary Model for data visibility, based on `read_only`, `contributor`, and `company_admin` roles.
- **Architectural Guardrails**: Asset Management Overview functions as a static record, linking to operational modules for live metrics.
- **Telemetry Module**: Project-scoped telemetry for Data Acquisition Systems (DAS) integration, health monitoring, and device mapping.
- **Document Versioning & Promotion System**: Manages lender-quality Data Room document versions with a "Promote to Current Assumptions" workflow, supporting `candidate`, `active`, and `retired` `ProjectFact` states with atomic transactions and diff computation.
- **Extraction Registry & Prompt Studio**: Scalable system for dynamic document type and field configuration using database-driven schemas and prompt templates, supporting re-extraction workflows.
- **In-App AI Parsing**: Fully in-app document parsing using Replit AI Integrations (OpenAI), featuring an `InAppParsingService` for file handling, text extraction, LLM calls via FastAPI BackgroundTasks, observability, and retry logic. Implements idempotency and concurrency safety with row locking and partial unique indexes. Quality guardrails enforce configurable settings for text length, file size, and LLM character limits.
- **Storage Service Abstraction**: Replit-native storage architecture with an abstract `StorageService` interface, supporting `ReplitStorageService`, optional `GCSStorageService`, and `HybridStorageService`.
- **Data Room Acceptance Safety**: Implements a parse run history panel for files and enforces acceptance safety rules, validating `run_id` and run status before allowing bulk acceptance of extracted data.
- **Contacts System**: A CRM-style contact management system for tracking external people related to portfolio, company, and project entities. Contacts are address book entries, not platform users, stored at three levels (portfolio, company, project) with exact-scope filtering and case-insensitive email uniqueness.
- **Finance Integration v1**: Company-level, read-only integration supporting multiple external providers with a pluggable architecture. Credentials are encrypted, and access is restricted to `company_admin` roles.

## External Dependencies
- **PostgreSQL**: Primary relational database.
- **Redis**: Used for caching and session management.
- **PowerBI**: Integrated for reporting and business intelligence.
- **Mailgun**: Configured for email services.
- **Rombus**: Integrated for camera/security functionalities.
- **AG Grid**: Enterprise license for advanced table functionalities.
- **OpenAI**: Utilized for in-app AI parsing capabilities.
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
- **Core Modules**: Workspace; Finance (capital governance, budgeting, vendor management) + read-only Finance Integration; Acquisitions (13-stage deal pipeline); Project Hub (unified asset management + due diligence); Access Control (multi-company effective-access resolver, role profiles, portfolio-hub boundary); Telemetry V2 (native PostgreSQL ingestion, interval rollups, in-process scheduler, manual refresh); Due Diligence Truth-Store + read-only Reconciliation Ladder; Document Versioning & Promotion; Expected Baselines (weather-adjusted physics); Native Weather Provenance (W0) + governed declarations; Device Eligibility classification; Native AI Assistant (read-only / propose-only); O&M / Device-Detail drill-down; and supporting systems (Contacts, Entity Directory, Project Import, Archive/Restore, Storage Abstraction, In-App AI Parsing, In-App Performance Report).
- **Key invariants**: "Site" is the canonical entity (Project == Site is a UI label only); telemetry/baseline/weather math never fabricates values (honest N/A, never 0); the AI Assistant and reconciliation views are strictly read-only; new feature surfaces are additive and flag-gated.
- **Detailed module reference**: See [`docs/architecture/backend-modules.md`](docs/architecture/backend-modules.md) for the full, per-module architecture (telemetry ingestion/scheduler, DD truth-store & reconciliation ladder, weather provenance, device eligibility, AI Assistant slices, O&M drill-down, and more).

## External Dependencies
- **PostgreSQL**: Primary relational database.
- **Redis**: Used for caching and session management.
- **PowerBI**: Integrated for reporting and business intelligence.
- **Mailgun**: Configured for email services.
- **Rombus**: Integrated for camera/security functionalities.
- **AG Grid**: Enterprise license for advanced table functionalities.
- **OpenAI**: Utilized for in-app AI parsing capabilities.
- 
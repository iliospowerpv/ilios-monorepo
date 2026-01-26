# iliOS - REA Investment Platform

## Overview
iliOS is a real estate asset investment management platform. It provides comprehensive tools for managing the entire lifecycle of real estate investments, from deal acquisition and due diligence to asset management, financial tracking, and reporting. The platform aims to streamline investment processes, enhance decision-making with data-driven insights, and improve operational efficiency for real estate investors and asset managers.

Key capabilities include:
- **User Authentication and Authorization**: Secure access control.
- **Asset Management**: Tracking and managing real estate assets.
- **Due Diligence**: Tools to support the diligence process for new acquisitions.
- **Task Management**: Organization of investment-related tasks.
- **Financial Management**: Budgeting, obligation tracking, and vendor management.
- **Sales Pipeline Management**: Tracking potential deals from prospecting to conversion.
- **Reporting**: Generating insights and reports on investment performance.

The platform is designed to be a critical tool for real estate professionals, offering a centralized system for investment oversight and operational governance.

## User Preferences
I prefer detailed explanations and thorough documentation for any implemented features or architectural decisions.
I expect iterative development, with clear communication before significant changes are made.
Do not change the fundamental "Site" entity in the backend; use "Project" only as a UI terminology update.

## System Architecture

**Frontend:**
- **Technology Stack**: React 18, TypeScript, Material UI (MUI) for component library, React Query for data fetching, React Router DOM for navigation, AG Grid for complex tables, Chart.js for data visualization, Webpack 5 for bundling.
- **Deployment**: Configured as a static deployment, building the React app and serving static files.
- **UI/UX Decisions**:
    - **Terminology Standardization**: All user-facing content uses "Projects" instead of "Sites" to improve clarity, while backend entities remain `sites`.
    - **Navigation Architecture**:
        1. **Entity Context Navigation (Top Bar)**: Displays `Portfolio → Company → Project` hierarchy, persists selection to `localStorage`, and dynamically enables/disables icons based on selected entity level.
        2. **Module Sidebar Navigation (Left)**: Permission-based visibility for modules like Asset Management, O&M, Due Diligence, Finance, Reports.
        3. **Breadcrumb Navigation (Header)**: Auto-generates from React Router `handle` patterns, resolving dynamic segments from URL parameters.
    - **Asset Management Overview**: Features a canonical site overview with drag-and-drop reordering, collapsible cards, persistence of state to `localStorage`, an executive summary, an underwriting readiness widget, and enhanced card headers with completeness indicators.
    - **Sidebar Layout Pattern**: Critical guidance for implementing collapsible sidebar navigation, ensuring main content and fixed headers correctly adapt to sidebar width changes using `marginLeft`, `width`, and `maxWidth` properties. Sidebar state is persisted to `localStorage`.

**Backend:**
- **Technology Stack**: Python 3.11, FastAPI for API development, SQLAlchemy for ORM, Alembic for database migrations, PostgreSQL as the primary database.
- **Core Modules**:
    - **Finance Module**: Capital governance, authorization, and compliance engine. Features budget vs. actual tracking, vendor visibility, authorization gating, approval workflows with audit trails, portfolio/fund rollups, and data room package export.
    - **Sales Module**: Manages a 14-stage deal acquisition pipeline, tracking deals separately until conversion into "Site" entities (referred to as "Projects" in the UI).
- **Architectural Guardrails (Asset Management Overview)**: The Asset Management Overview page is designed as a static site record and readiness surface, intentionally avoiding operational data leakage, telemetry, or live performance data. It clearly defines cross-module boundaries, linking to operations modules for live metrics rather than embedding them.

## External Dependencies
- **PostgreSQL**: Used as the primary relational database (Replit built-in for production, separate setup for development).
- **Redis**: Upstash with TLS, used for caching and session management.
- **PowerBI**: Integrated for reporting and business intelligence.
- **Mailgun**: Configured for email services (US region, domain: iliospower.com).
- **Rombus**: Integrated for camera/security functionalities.
- **AG Grid**: Enterprise license configured for advanced table functionalities.
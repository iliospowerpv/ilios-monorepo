import { HelpArticle } from '../types';

export const gettingStartedArticles: HelpArticle[] = [
  {
    slug: 'projects-vs-deals',
    title: 'Understanding Projects vs Deals',
    summary:
      'Learn the difference between deals and projects in Ilios, and how they relate to each other throughout the investment lifecycle.',
    category: 'getting-started',
    audience: ['all-users'],
    articleType: 'guide',
    tags: ['deals', 'projects', 'basics', 'lifecycle'],
    searchKeywords: ['deal', 'project', 'difference', 'convert', 'acquisition', 'pipeline'],
    relatedArticles: ['lifecycle-stages', 'navigation-guide', 'deal-to-project-conversion'],
    lastUpdated: '2026-04-01',
    body: `## What Is a Deal?

A **deal** represents a potential investment opportunity that is being evaluated through the acquisitions pipeline. Deals are tracked in the **Acquisitions** module and progress through stages such as Screening, Evaluation, LOI, and Under Contract.

Deals contain preliminary information about a potential solar, wind, or storage project including location, capacity, expected returns, and counterparty details. During the deal phase, your team conducts initial assessments before committing resources.

## What Is a Project?

A **project** (also called a "site") is a confirmed investment that has been onboarded into the Ilios platform for active management. Projects appear in the **Project Hub** and have access to the full suite of modules including Data Room, O&M monitoring, Finance tracking, and Tasks.

Projects contain detailed operational data such as device telemetry, financial actuals, documents, and task workflows.

## How They Relate

The typical flow is:

1. A new opportunity enters Ilios as a **Deal** in Acquisitions
2. The deal progresses through evaluation stages
3. Once approved, the deal is **converted to a Project**
4. The project is then managed through its operational lifecycle

Not all projects start as deals — some may be directly onboarded if they were acquired outside the platform.

## Key Differences

| Aspect | Deal | Project |
|--------|------|---------|
| Module | Acquisitions | Project Hub |
| Purpose | Evaluate opportunity | Manage active investment |
| Data depth | Preliminary | Comprehensive |
| Lifecycle | Pipeline stages | Operational stages |
| Modules available | Limited | Full suite (O&M, Finance, Data Room, Tasks) |

## When Does Conversion Happen?

Deal-to-project conversion typically occurs when:
- Due diligence is complete
- Financial approval has been granted
- The acquisition closes

Your administrator or acquisitions lead initiates the conversion, which creates a new project record and migrates relevant deal data.`
  },
  {
    slug: 'navigation-guide',
    title: 'Navigating the Ilios Platform',
    summary:
      'A complete guide to the Ilios navigation structure including the sidebar, modules, breadcrumbs, and entity hierarchy.',
    category: 'getting-started',
    audience: ['all-users'],
    articleType: 'guide',
    tags: ['navigation', 'sidebar', 'modules', 'breadcrumbs', 'basics'],
    searchKeywords: ['navigate', 'menu', 'sidebar', 'breadcrumb', 'find', 'where', 'module', 'page'],
    relatedArticles: ['portfolio-company-project-hierarchy', 'projects-vs-deals', 'module-activation'],
    lastUpdated: '2026-04-01',
    body: `## The Sidebar Navigation

The left sidebar is your primary navigation tool. It contains icons and labels for each major module:

- **Home** — Your personalized dashboard with key metrics and recent activity
- **Acquisitions** — Deal pipeline and acquisition tracking
- **Project Hub** — Central management for all projects (overview, details, company views)
- **Data Room** — Document management and due diligence files
- **O&M** — Operations and maintenance monitoring
- **Finance** — Financial tracking, budgets, and readiness
- **Tasks** — Task management across projects
- **Reports** — Portfolio-wide and project-level reporting
- **Portfolio Admin** — Administrative settings and configuration

The sidebar can be collapsed to show only icons, giving you more screen space.

## Breadcrumbs and Entity Navigation

At the top of most pages, you will see **breadcrumbs** showing your current location in the hierarchy. For example:

\`Portfolio > Acme Solar Co. > Desert Sun Project > O&M\`

Click any level in the breadcrumb to navigate back up the hierarchy.

## The Entity Hierarchy

Ilios organizes data in a three-level hierarchy:

1. **Portfolio** — The top level, representing your entire investment portfolio
2. **Company** — A legal entity or SPV that owns one or more projects
3. **Project** — An individual renewable energy site or asset

Most modules let you view data at any level. For example, Finance can show portfolio-level rollups, company-level summaries, or project-level details.

## Module Access

Some modules require you to select a project first (like Data Room, O&M, and Tasks). If you click one of these without a project selected, a project picker dialog will appear.

Other modules (Home, Acquisitions, Finance, Reports, Portfolio Admin) work at the portfolio level and don't require a project selection.

## Quick Navigation Tips

- Use the **entity navigation** in the header to quickly switch between companies and projects
- The **Home** page shows your most recent activity and quick links
- Use **keyboard shortcuts** where available to navigate faster
- The **Help & Resources** section (accessible from the user menu) provides documentation for every module`
  },
  {
    slug: 'lifecycle-stages',
    title: 'Lifecycle Stages Explained',
    summary:
      'Understand the lifecycle stages that projects move through in Ilios, from early development through operations and eventual decommissioning.',
    category: 'getting-started',
    audience: ['all-users'],
    articleType: 'concept',
    tags: ['lifecycle', 'stages', 'status', 'project'],
    searchKeywords: ['lifecycle', 'stage', 'status', 'development', 'construction', 'operation', 'NTP', 'COD'],
    relatedArticles: ['projects-vs-deals', 'module-activation', 'status-definitions'],
    lastUpdated: '2026-04-01',
    body: `## Overview

Every project in Ilios has a **lifecycle stage** that indicates where it is in its journey from initial development to full operation. The lifecycle stage determines which modules are active and what data is relevant.

## The Lifecycle Stages

### 1. Development
The project is in early planning phases. Site assessments, permitting, and initial engineering work are underway. Key activities include land acquisition, interconnection applications, and environmental reviews.

### 2. Pre-Construction
Engineering is finalized and procurement is beginning. The project has received its permits and is preparing for construction. Financing may still be in progress.

### 3. Construction
Active building is underway. Equipment is being installed, and the project is moving toward mechanical completion. Construction progress is tracked through milestones and tasks.

### 4. Commissioning
The project is being tested and validated. Systems are energized, performance tests are conducted, and punch list items are resolved. This stage bridges construction and operations.

### 5. Notice to Proceed (NTP)
A formal milestone indicating the project has met all conditions to begin operations. This often triggers financial obligations and warranty periods.

### 6. Commercial Operation Date (COD)
The project is fully operational and generating revenue. This is a critical financial milestone that activates monitoring, O&M tracking, and financial reporting.

### 7. Operations
The project is in its steady-state operational phase. O&M teams monitor performance, handle work orders, and maintain equipment. Financial actuals are tracked against budgets.

### 8. Decommissioning
End-of-life phase where the project is being retired. Equipment removal, site restoration, and final financial reconciliation occur.

## How Stages Affect the Platform

Different lifecycle stages activate different modules:

| Stage | Key Active Modules |
|-------|-------------------|
| Development | Acquisitions, Data Room |
| Pre-Construction | Project Hub, Data Room, Finance |
| Construction | Project Hub, Tasks, Finance |
| Commissioning | Project Hub, Tasks, O&M |
| Operations | All modules active |
| Decommissioning | Finance, Tasks |

## Changing a Project's Stage

Lifecycle stage changes are typically managed by administrators through the Portfolio Admin module. Stage transitions may trigger automated workflows such as activating new modules or sending notifications.`
  },
  {
    slug: 'module-activation',
    title: 'When Modules Become Active',
    summary:
      'Learn which modules are available at different project lifecycle stages and how module access is controlled.',
    category: 'getting-started',
    audience: ['all-users'],
    articleType: 'guide',
    tags: ['modules', 'activation', 'lifecycle', 'access'],
    searchKeywords: ['module', 'active', 'available', 'disabled', 'grayed', 'access', 'permission', 'locked'],
    relatedArticles: ['lifecycle-stages', 'permissions-and-access', 'navigation-guide'],
    lastUpdated: '2026-04-01',
    body: `## How Module Activation Works

Not all modules are available for every project at all times. Module availability depends on two factors:

1. **Lifecycle stage** — The project's current stage determines which modules are relevant
2. **User permissions** — Your role determines which modules you can access

## Module Availability by Stage

### Always Available
- **Home** — Available to all authenticated users
- **Reports** — Available once a project exists
- **Portfolio Admin** — Available to administrators

### Acquisitions Phase
- **Acquisitions** — Active during deal evaluation
- **Data Room** — Available for due diligence documents

### Construction & Pre-Operations
- **Project Hub** — Active once a project is created
- **Data Room** — Active for document management
- **Tasks** — Active for construction tracking
- **Finance** — Active for budget setup

### Operations Phase
- **O&M** — Active once the project reaches COD
- **Finance** — Full financial tracking with actuals
- **All other modules** — Fully active

## Why Is a Module Grayed Out?

If you see a module icon that appears disabled (grayed out) in the sidebar, it could mean:

1. **No permission** — Your role doesn't include access to that module. Contact your administrator.
2. **No project selected** — Some modules require a project context. Click the module to open the project picker.
3. **Lifecycle restriction** — The project hasn't reached the stage where that module becomes relevant.

## Requesting Access

If you need access to a module you can't currently see, contact your portfolio administrator. They can adjust your role permissions through the Portfolio Admin module.`
  },
  {
    slug: 'permissions-and-access',
    title: 'Permissions & Access Control',
    summary:
      'How roles, permissions, and access control work in Ilios to protect sensitive data and manage user capabilities.',
    category: 'getting-started',
    audience: ['all-users', 'admin'],
    articleType: 'guide',
    tags: ['permissions', 'access', 'roles', 'security', 'admin'],
    searchKeywords: ['permission', 'access', 'role', 'admin', 'view', 'edit', 'restricted', 'cannot see', 'locked out'],
    relatedArticles: ['module-activation', 'portfolio-admin-overview', 'troubleshooting-permissions'],
    lastUpdated: '2026-04-01',
    body: `## Role-Based Access Control

Ilios uses a **role-based access control (RBAC)** system. Each user is assigned a role that defines what they can see and do across the platform.

## How Roles Work

A role is a collection of permissions organized by module. Each module permission has two levels:

- **View** — Can see and read data in the module
- **Edit** — Can create, modify, and delete data in the module

For example, a user with "Finance: View" can see financial data but cannot edit budgets or actuals.

## Common Roles

While roles are customizable, common configurations include:

### Portfolio Manager
Full access to all modules with view and edit permissions. Can manage projects, review finances, and oversee operations.

### Operations Manager
View and edit access to O&M, Tasks, and Project Hub. View-only access to Finance and Reports.

### Financial Analyst
Full access to Finance and Reports. View-only access to Project Hub and Acquisitions.

### Viewer
Read-only access across all permitted modules. Cannot create or modify data.

### Administrator
Full access to all modules including Portfolio Admin and system settings.

## What Controls What You See

Your experience in Ilios is shaped by:

1. **Module permissions** — Which sidebar items are accessible
2. **Data scope** — Which companies and projects you can view
3. **Action permissions** — Whether you can edit, create, or delete records

## Managing Roles

Administrators can create and modify roles through the **Portfolio Admin** module. Changes to a user's role take effect immediately.

## Tips

- If you see a "You don't have permission" message, check with your administrator about your role assignment
- Some actions require specific module-level edit permissions
- System users have elevated access for platform-wide administration`
  },
  {
    slug: 'portfolio-company-project-hierarchy',
    title: 'Portfolio, Company & Project Hierarchy',
    summary:
      'Understand how Ilios organizes investments into a three-level hierarchy of portfolios, companies, and projects.',
    category: 'getting-started',
    audience: ['all-users'],
    articleType: 'concept',
    tags: ['hierarchy', 'portfolio', 'company', 'project', 'organization'],
    searchKeywords: [
      'portfolio',
      'company',
      'project',
      'hierarchy',
      'structure',
      'organization',
      'SPV',
      'site',
      'asset'
    ],
    relatedArticles: ['navigation-guide', 'projects-vs-deals', 'asset-hierarchy-explained'],
    lastUpdated: '2026-04-01',
    body: `## The Three-Level Hierarchy

Ilios organizes all investment data in a clear three-level hierarchy:

### Portfolio (Top Level)
Your **portfolio** represents the entire collection of investments managed through Ilios. It's the broadest view available, providing rollup metrics across all companies and projects.

Think of the portfolio as your "organization" level — it encompasses everything.

### Company (Middle Level)
A **company** represents a legal entity, special purpose vehicle (SPV), or subsidiary that owns one or more projects. Companies are used to:

- Group related projects under their legal owner
- Track company-level financials and compliance
- Manage company-specific settings and contacts

### Project / Site (Lowest Level)
A **project** (sometimes called a "site" or "asset") is an individual renewable energy installation. This is where the most detailed data lives:

- Physical location and capacity
- Device telemetry and performance
- Financial actuals and budgets
- Documents and due diligence records
- Work orders and maintenance tasks

## How the Hierarchy Works in Practice

Most modules in Ilios support viewing data at any level:

- **Portfolio level** — Aggregated metrics across all companies and projects
- **Company level** — Summary for a specific company and its projects
- **Project level** — Detailed data for an individual site

You can navigate between levels using breadcrumbs, the entity navigation in the header, or by drilling down from summary views.

## Example Structure

\`\`\`
My Portfolio
├── SunCo Holdings (Company)
│   ├── Desert Sun Solar Farm (Project)
│   └── Mountain Wind Park (Project)
└── GreenPower LLC (Company)
    ├── Valley Storage Facility (Project)
    └── Coastal Wind Project (Project)
\`\`\`

## Scoped Views

Many modules support a "scoped" view that lets you focus on a specific level. The scope selector in the header allows you to switch between portfolio, company, and project-level views without navigating away from the current module.`
  }
];

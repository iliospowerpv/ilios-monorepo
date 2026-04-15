import { HelpArticle } from '../types';

export const projectHubArticles: HelpArticle[] = [
  {
    slug: 'project-hub-overview',
    title: 'Project Hub Overview',
    summary:
      'The central hub for managing all your projects and companies, with access to overview, data room, O&M, finance, and tasks.',
    category: 'project-hub',
    module: 'project-hub',
    audience: ['all-users', 'asset-manager'],
    articleType: 'overview',
    tags: ['project-hub', 'projects', 'companies', 'overview', 'management'],
    searchKeywords: ['project hub', 'asset management', 'projects', 'companies', 'sites', 'central', 'hub'],
    relatedArticles: ['project-hub-workflows', 'portfolio-company-project-hierarchy', 'project-hub-key-screens'],
    lastUpdated: '2026-04-01',
    body: `## What Is the Project Hub?

The **Project Hub** is the central management module for all your projects and companies in Ilios. It provides a unified view of your portfolio with the ability to drill down into individual companies and projects.

## Key Features

### Portfolio Overview
The top-level Project Hub view shows:
- Total number of companies and projects
- Aggregate capacity and performance metrics
- Status distribution across your portfolio

### Company Management
At the company level, you can:
- View all projects belonging to a company
- See company-level summary metrics
- Manage company-specific tasks and settings

### Project Details
Each project in the Project Hub has a tabbed interface with:
- **Overview** — Key project information, location, capacity, and status
- **Data Room** — Document management and due diligence
- **O&M** — Operations and maintenance monitoring
- **Finance** — Financial tracking and readiness
- **Tasks** — Project-specific task management

### Scoped Navigation
Use the scope selector to switch between:
- Portfolio-wide view of all companies and projects
- Company-level view for a specific entity
- Project-level detail view

## Who Uses It

- **Asset Managers** — Primary users for day-to-day project oversight
- **Project Managers** — Manage specific projects and their details
- **Executives** — High-level portfolio health monitoring
- **All team members** — Access project information relevant to their role

## Important Terms

- **Site** — Another term for a project, referring to the physical installation location
- **Company** — The legal entity that owns one or more projects
- **Tab** — The different views available within a project (Overview, Data Room, O&M, Finance, Tasks)`
  },
  {
    slug: 'project-hub-workflows',
    title: 'Project Hub Workflows',
    summary:
      'Common workflows in the Project Hub including reviewing projects, managing company portfolios, and navigating the hierarchy.',
    category: 'project-hub',
    module: 'project-hub',
    audience: ['asset-manager'],
    articleType: 'tutorial',
    tags: ['project-hub', 'workflow', 'projects', 'companies'],
    searchKeywords: ['project hub workflow', 'review project', 'manage company', 'view projects', 'find project'],
    relatedArticles: ['project-hub-overview', 'project-hub-key-screens', 'navigation-guide'],
    lastUpdated: '2026-04-01',
    body: `## Reviewing Your Portfolio

1. Navigate to **Project Hub** from the sidebar
2. The overview tab shows all companies and summary metrics
3. Use the sites tab to see all projects across companies
4. Click on any company or project to drill down

## Finding a Specific Project

1. Go to the Project Hub overview
2. Use the sites tab to see all projects
3. Use the search or filter options to narrow results
4. Click the project name to open its detail page

## Reviewing a Project's Status

1. Navigate to the project's detail page
2. The **Overview** tab shows:
   - Current lifecycle stage
   - Key performance metrics
   - Location and capacity information
   - Recent activity
3. Switch between tabs to see different aspects of the project

## Navigating Between Company and Project Views

1. From the portfolio level, click a company name to see its projects
2. From a company view, click a project to see its details
3. Use breadcrumbs at the top to navigate back up the hierarchy
4. Use the scope selector to quickly switch context levels

## Managing Tasks from the Project Hub

1. Open a project or company
2. Navigate to the **Tasks** tab
3. View, create, and manage tasks specific to that entity
4. Filter tasks by status, assignee, or priority`
  },
  {
    slug: 'project-hub-key-screens',
    title: 'Project Hub Key Screens',
    summary: 'A walkthrough of the main screens in the Project Hub module.',
    category: 'project-hub',
    module: 'project-hub',
    audience: ['asset-manager'],
    articleType: 'guide',
    tags: ['project-hub', 'screens', 'interface'],
    searchKeywords: ['project hub screen', 'project list', 'company view', 'project detail', 'tabs'],
    relatedArticles: ['project-hub-overview', 'project-hub-workflows'],
    lastUpdated: '2026-04-01',
    body: `## Portfolio-Level View

The top-level Project Hub shows:
- **Overview tab** — Summary cards with portfolio-wide metrics
- **Sites tab** — Filterable table of all projects across companies
- Company cards linking to individual company views

## Company Detail View

Clicking a company shows:
- **Overview** — Company information and aggregate metrics
- **Sites** — Projects belonging to this company
- **Tasks** — Company-level tasks

## Project Detail View

The project detail page uses a tabbed interface:

### Overview Tab
- Project name, location, and capacity
- Lifecycle stage indicator
- Key performance metrics
- Technology type and configuration

### Data Room Tab
- Document categories and file listings
- Upload functionality for new documents
- Due diligence tracking

### O&M Tab
- Device monitoring and alerts
- Performance metrics (availability, PR)
- Work order management

### Finance Tab
- Budget vs actual comparisons
- Revenue and cost tracking
- Financial readiness scores

### Tasks Tab
- Project-specific task list
- Task creation and assignment
- Status and priority management`
  },
  {
    slug: 'project-hub-troubleshooting',
    title: 'Project Hub Troubleshooting',
    summary: 'Solutions for common Project Hub issues.',
    category: 'project-hub',
    module: 'project-hub',
    audience: ['asset-manager'],
    articleType: 'troubleshooting',
    tags: ['project-hub', 'troubleshooting'],
    searchKeywords: ['project hub problem', 'project not showing', 'cannot access project', 'tabs missing'],
    relatedArticles: ['project-hub-overview', 'troubleshooting-permissions', 'troubleshooting-missing-data'],
    lastUpdated: '2026-04-01',
    body: `## I Can't Find a Project

**Possible causes:**
- The project may belong to a company you don't have access to
- Filters may be hiding the project
- The project may not have been created yet (it might still be a deal in Acquisitions)

**Solution:** Clear all filters and check the sites tab at the portfolio level. If the project still doesn't appear, verify with your administrator that you have access.

## Project Tabs Are Missing

**Cause:** Some tabs only appear based on the project's lifecycle stage or your permissions.

**Solution:** Check the project's lifecycle stage — O&M tabs may not appear for projects still in development. Verify your permissions include access to the relevant modules.

## Project Data Looks Outdated

**Cause:** Data may be cached or the underlying data source may not have been updated.

**Solution:** Refresh the page. If data still appears stale, check when the data was last updated (shown in metadata). Some data sources update on schedules rather than in real-time.

## Can't Edit Project Information

**Cause:** You may have view-only permissions for the Project Hub.

**Solution:** Contact your administrator to request edit access to the Project Hub or Asset Management module.`
  }
];

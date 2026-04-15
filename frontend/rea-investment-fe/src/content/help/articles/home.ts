import { HelpArticle } from '../types';

export const homeArticles: HelpArticle[] = [
  {
    slug: 'home-overview',
    title: 'Home Module Overview',
    summary:
      'Your personalized dashboard providing key metrics, recent activity, and quick access to important items across your portfolio.',
    category: 'home',
    module: 'home',
    audience: ['all-users'],
    articleType: 'overview',
    tags: ['home', 'dashboard', 'overview', 'landing'],
    searchKeywords: ['home', 'dashboard', 'landing', 'start', 'overview', 'metrics', 'activity'],
    relatedArticles: ['navigation-guide', 'home-workflows'],
    lastUpdated: '2026-04-01',
    body: `## What Is the Home Module?

The **Home** module is your landing page when you log into Ilios. It provides a personalized overview of your portfolio with key metrics, recent activity, and quick access to items that need your attention.

## Key Features

### Portfolio Summary
At the top of the Home page, you'll see high-level metrics for your portfolio including total capacity, number of active projects, and performance indicators.

### Recent Activity
A feed showing recent changes across your portfolio — new tasks assigned, document uploads, status changes, and other updates relevant to your role.

### Quick Actions
Shortcuts to common tasks like creating new deals, viewing reports, or accessing frequently used projects.

### Alerts and Notifications
Important items that need your attention, such as overdue tasks, performance alerts, or pending approvals.

## Who Uses It

Every user sees the Home module, but the content is tailored to your role and permissions. A finance user will see financial metrics prominently, while an operations manager will see O&M alerts and performance data.

## Tips

- Check Home daily for a quick snapshot of portfolio health
- Use the quick action buttons to jump directly to common workflows
- Review the activity feed to stay informed about changes made by your team`
  },
  {
    slug: 'home-workflows',
    title: 'Common Home Page Workflows',
    summary: 'How to use the Home page effectively for daily portfolio management and task prioritization.',
    category: 'home',
    module: 'home',
    audience: ['all-users'],
    articleType: 'tutorial',
    tags: ['home', 'workflow', 'daily', 'tasks'],
    searchKeywords: ['home', 'workflow', 'daily', 'morning', 'check', 'routine', 'task'],
    relatedArticles: ['home-overview', 'navigation-guide'],
    lastUpdated: '2026-04-01',
    body: `## Daily Check-In Workflow

The Home page is designed to support a quick daily review:

1. **Review portfolio metrics** — Check the summary cards for any significant changes
2. **Scan the activity feed** — Look for recent changes that affect your work
3. **Check alerts** — Address any notifications or overdue items
4. **Navigate to priority items** — Use quick links to jump to the most important tasks

## Finding What Needs Attention

The Home page highlights items that need your attention:

- **Overdue tasks** appear with warning indicators
- **Performance alerts** from O&M monitoring are surfaced
- **Pending approvals** show items waiting for your review
- **Recent uploads** indicate new documents to review

## Customizing Your View

While the Home page layout is standardized, the content adapts to your role. The metrics and activity items shown are filtered based on:

- Your module permissions
- Your assigned companies and projects
- Your role in the organization`
  },
  {
    slug: 'home-key-screens',
    title: 'Home Key Screens',
    summary: 'A walkthrough of the main elements on the Home page.',
    category: 'home',
    module: 'home',
    audience: ['all-users'],
    articleType: 'guide',
    tags: ['home', 'screens', 'interface', 'dashboard'],
    searchKeywords: ['home screen', 'dashboard layout', 'home page sections', 'home interface'],
    relatedArticles: ['home-overview', 'home-workflows'],
    lastUpdated: '2026-04-01',
    body: `## Portfolio Summary Cards

At the top of the Home page, summary cards display:
- **Total Projects** — Count of active projects in your portfolio
- **Total Capacity** — Aggregate installed capacity (MW)
- **Performance Indicators** — Key metrics like portfolio-wide availability

## Activity Feed

Below the summary cards, the activity feed shows:
- Recent changes across your portfolio
- Items organized chronologically
- Action indicators showing creates, updates, and status changes
- Quick links to navigate to the affected item

## Quick Actions Panel

Shortcuts for common actions:
- Create a new deal in Acquisitions
- View the latest reports
- Navigate to frequently accessed projects
- Open task management

## Alerts Section

Active alerts and notifications:
- Overdue tasks with warning badges
- Performance alerts from O&M monitoring
- Pending approval items
- System notifications

## Your Projects Widget

A card-based view of projects you have access to:
- Project name and company
- Key status indicators
- Quick navigation to project details`
  },
  {
    slug: 'home-troubleshooting',
    title: 'Home Troubleshooting',
    summary: 'Common Home page issues and how to resolve them.',
    category: 'home',
    module: 'home',
    audience: ['all-users'],
    articleType: 'troubleshooting',
    tags: ['home', 'troubleshooting'],
    searchKeywords: ['home problem', 'dashboard empty', 'home not loading', 'home blank', 'no activity'],
    relatedArticles: ['home-overview', 'troubleshooting-empty-dashboards', 'troubleshooting-permissions'],
    lastUpdated: '2026-04-01',
    body: `## Home Page Shows No Data

**Possible causes:**
- Your account may be newly created with no projects assigned
- Your role may not include access to any modules
- Data sources may not be connected yet

**Solution:** Contact your administrator to verify your account has projects assigned and appropriate role permissions set.

## Activity Feed Is Empty

**Possible causes:**
- No recent activity has occurred in your assigned projects
- Your permissions may limit which activity you can see

**Solution:** Verify you have access to projects with active data. Activity is generated when team members make changes to projects you can access.

## Portfolio Metrics Look Wrong

**Possible causes:**
- Metrics may be aggregated from a subset of projects based on your permissions
- Data refresh may be pending

**Solution:** Check that you have access to all expected projects. Refresh the page to load the latest calculations.

## Quick Actions Not Working

**Cause:** The target module for the quick action may require permissions you don't have.

**Solution:** Verify your role includes access to the module the quick action targets (e.g., Acquisitions for "Create Deal").`
  },
  {
    slug: 'home-terms',
    title: 'Home Important Terms',
    summary: 'Key terms and concepts used on the Home page.',
    category: 'home',
    module: 'home',
    audience: ['all-users'],
    articleType: 'reference',
    tags: ['home', 'terms', 'definitions'],
    searchKeywords: ['home terms', 'dashboard terms', 'home definitions', 'home concepts'],
    relatedArticles: ['home-overview', 'field-definitions'],
    lastUpdated: '2026-04-01',
    body: `## Key Terms

### Portfolio Summary
Aggregated metrics across all projects you have access to, shown as summary cards at the top of the Home page.

### Activity Feed
A chronological list of recent changes and events across your portfolio, filtered by your permissions and access scope.

### Quick Actions
Shortcut buttons that navigate directly to common workflows in other modules, saving clicks and navigation time.

### Alerts
Notifications about items requiring your attention — overdue tasks, performance issues, pending approvals, or system events.

### Your Projects
A widget showing the projects assigned to your access scope, with key status indicators and quick navigation links.

### Dashboard
The general term for the Home page view, providing an at-a-glance overview of portfolio health and activity.`
  }
];

import { HelpArticle } from '../types';

export const reportsArticles: HelpArticle[] = [
  {
    slug: 'reports-overview',
    title: 'Reports Module Overview',
    summary:
      'Generate and view reports across your portfolio including performance, financial, and operational reports.',
    category: 'reports',
    module: 'reports',
    audience: ['all-users'],
    articleType: 'overview',
    tags: ['reports', 'reporting', 'analytics', 'dashboards'],
    searchKeywords: ['reports', 'reporting', 'analytics', 'dashboard', 'chart', 'export', 'pdf', 'data'],
    relatedArticles: ['reports-workflows', 'reports-key-screens', 'portfolio-rollups-explained'],
    lastUpdated: '2026-04-01',
    body: `## What Is the Reports Module?

The **Reports** module provides portfolio-wide reporting capabilities, allowing you to generate, view, and export reports across various dimensions of your renewable energy investments.

## Key Features

### Report Types
- **Performance reports** — Generation, availability, and PR metrics
- **Financial reports** — Revenue, costs, budget vs actual comparisons
- **Operational reports** — Work orders, tasks, and maintenance summaries
- **Portfolio reports** — Cross-project and cross-company analytics

### Scoped Reporting
View reports at different levels:
- **Portfolio scope** — Aggregate data across everything
- **Company scope** — Focused on a single company
- **Project scope** — Detailed for an individual project

### Data Visualization
- Charts and graphs for trend analysis
- Summary cards with key metrics
- Tabular data with sorting and filtering

### Export Capabilities
- Export report data for external use
- Share reports with stakeholders

## Who Uses It

- **Executives** — Portfolio-wide performance reviews
- **Asset Managers** — Project performance tracking
- **Finance teams** — Financial reporting and analysis
- **Operations teams** — Operational summaries

## Important Terms

- **Scope** — The level at which a report is generated (portfolio, company, project)
- **Rollup** — Aggregated metrics from lower levels to higher levels
- **KPI** — Key Performance Indicator, a measurable value showing performance`
  },
  {
    slug: 'reports-workflows',
    title: 'Reports Workflows',
    summary: 'How to generate, view, and use reports effectively.',
    category: 'reports',
    module: 'reports',
    audience: ['all-users'],
    articleType: 'tutorial',
    tags: ['reports', 'workflow', 'generate', 'view'],
    searchKeywords: ['generate report', 'view report', 'export report', 'create report', 'run report'],
    relatedArticles: ['reports-overview', 'reports-key-screens'],
    lastUpdated: '2026-04-01',
    body: `## Viewing Portfolio Reports

1. Navigate to the **Reports** module from the sidebar
2. The default view shows portfolio-level reports
3. Browse available report types
4. Select a report to view its data

## Changing Report Scope

1. Use the scope selector in the header
2. Choose portfolio, company, or project level
3. The report data will refresh for the selected scope

## Analyzing Report Data

1. Review the summary cards for key takeaways
2. Examine charts for trend patterns
3. Use the data table for detailed figures
4. Sort and filter to focus on specific areas

## Exporting Reports

1. Navigate to the desired report
2. Configure the scope and filters
3. Use the export function to download data
4. Choose the appropriate format for your needs

## Comparing Across Periods

1. Select a report with time-based data
2. Use the date range selector
3. Compare metrics across different time periods
4. Identify trends and anomalies`
  },
  {
    slug: 'reports-key-screens',
    title: 'Reports Key Screens',
    summary: 'Overview of the Reports module interface.',
    category: 'reports',
    module: 'reports',
    audience: ['all-users'],
    articleType: 'guide',
    tags: ['reports', 'screens', 'interface'],
    searchKeywords: ['reports screen', 'report view', 'report dashboard', 'report list'],
    relatedArticles: ['reports-overview', 'reports-workflows'],
    lastUpdated: '2026-04-01',
    body: `## Reports Home

The main Reports page shows:
- **Available reports** — List of report types you can access
- **Scope selector** — Choose portfolio, company, or project level
- **Recent reports** — Quick access to recently viewed reports

## Report Detail View

Individual reports display:
- **Summary metrics** — Key figures in card format
- **Visualizations** — Charts, graphs, and trend lines
- **Data table** — Detailed tabular data with sorting and filtering
- **Export options** — Download or share the report data

## Scoped Views

Reports adapt based on scope:
- **Portfolio** — Aggregated across all companies and projects
- **Company** — Filtered to a specific company's projects
- **Project** — Detailed data for a single project`
  },
  {
    slug: 'reports-troubleshooting',
    title: 'Reports Troubleshooting',
    summary: 'Common reporting issues and solutions.',
    category: 'reports',
    module: 'reports',
    audience: ['all-users'],
    articleType: 'troubleshooting',
    tags: ['reports', 'troubleshooting'],
    searchKeywords: ['report problem', 'report empty', 'data mismatch', 'report wrong', 'export failed'],
    relatedArticles: ['reports-overview', 'troubleshooting-report-mismatches', 'troubleshooting-empty-dashboards'],
    lastUpdated: '2026-04-01',
    body: `## Report Shows No Data

**Possible causes:**
- The selected scope may not have data for the chosen period
- Your permissions may limit the data visible to you
- Data may not have been entered for the selected metrics

**Solution:** Verify the date range and scope settings. Try broadening the scope to portfolio level. Check that data exists for the selected period.

## Report Numbers Don't Match Other Modules

**Possible causes:**
- Reports may use different calculation periods
- Rollup calculations may include/exclude certain items
- Data refresh timing may differ between modules

**Solution:** Check the report's date range and compare with the same period in other modules. Report rollups may aggregate differently than individual module views. See the Portfolio Rollups concept article.

## Cannot Access Certain Reports

**Cause:** Your role may not include Reports view permissions, or specific report types may require additional module access.

**Solution:** Contact your administrator to verify your reporting permissions.

## Export Is Not Working

**Possible causes:**
- Browser popup blockers may be preventing the download
- The report may have too much data to export at once

**Solution:** Check your browser's popup blocker settings. Try narrowing the report scope or date range before exporting.`
  }
];

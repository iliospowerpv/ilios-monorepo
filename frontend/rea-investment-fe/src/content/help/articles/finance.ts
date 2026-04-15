import { HelpArticle } from '../types';

export const financeArticles: HelpArticle[] = [
  {
    slug: 'finance-overview',
    title: 'Finance Module Overview',
    summary:
      'Track financial performance across your portfolio including budgets, actuals, revenue, costs, and financial readiness.',
    category: 'finance',
    module: 'finance',
    audience: ['all-users', 'finance'],
    articleType: 'overview',
    tags: ['finance', 'budget', 'actuals', 'revenue', 'costs', 'readiness'],
    searchKeywords: ['finance', 'budget', 'actual', 'revenue', 'cost', 'financial', 'money', 'readiness', 'variance'],
    relatedArticles: [
      'finance-workflows',
      'finance-readiness-explained',
      'budget-vs-actual-explained',
      'finance-key-screens'
    ],
    lastUpdated: '2026-04-01',
    body: `## What Is the Finance Module?

The **Finance** module provides comprehensive financial tracking and analysis for your renewable energy portfolio. It enables teams to monitor budgets, track actuals, analyze variances, and assess financial readiness across all projects.

## Key Features

### Portfolio Financial Overview
- Aggregate financial metrics across all companies and projects
- Revenue and cost summaries
- Budget vs actual comparisons at every level

### Company-Level Finance
- Financial summaries for individual companies
- Cross-project comparisons within a company
- Company-level budget tracking

### Project-Level Finance
- Detailed budget line items
- Actual revenue and cost tracking
- Variance analysis (budget vs actual)
- Financial readiness scoring

### Financial Readiness
A scoring system that evaluates how prepared a project's financial data is for reporting and decision-making. The readiness score considers:
- Completeness of budget data
- Timeliness of actual data entry
- Data quality and consistency

### Scoped Views
Switch between portfolio, company, and project-level financial views using the scope selector.

## Who Uses It

- **Finance teams** — Primary users for budget management and financial tracking
- **CFOs and Controllers** — Financial oversight and reporting
- **Asset Managers** — Project-level financial performance monitoring
- **Executives** — Portfolio-wide financial health assessment

## Important Terms

- **Budget** — Planned financial figures (revenue, costs) for a period
- **Actuals** — Real financial figures recorded from operations
- **Variance** — The difference between budget and actual figures
- **Financial Readiness** — A score indicating data completeness for financial reporting`
  },
  {
    slug: 'finance-workflows',
    title: 'Finance Workflows',
    summary: 'Common financial workflows including reviewing budgets, entering actuals, and analyzing variances.',
    category: 'finance',
    module: 'finance',
    audience: ['finance'],
    articleType: 'tutorial',
    tags: ['finance', 'workflow', 'budget', 'actuals', 'variance'],
    searchKeywords: ['enter actuals', 'review budget', 'compare budget', 'financial review', 'variance analysis'],
    relatedArticles: ['finance-overview', 'finance-key-screens', 'budget-vs-actual-explained'],
    lastUpdated: '2026-04-01',
    body: `## Reviewing Portfolio Financials

1. Navigate to the **Finance** module from the sidebar
2. The landing page shows portfolio-level financial summary
3. Review key metrics: total revenue, total costs, overall variance
4. Identify companies or projects with significant variances
5. Drill into specific entities for detailed analysis

## Reviewing Project-Level Finances

1. From the Finance landing, click on a company
2. Then select a specific project/site
3. Review the budget vs actual comparison
4. Analyze line-item variances
5. Check the financial readiness score

## Analyzing Variances

1. Navigate to a project's finance view
2. Look for line items where actuals differ significantly from budget
3. Review the variance percentage and absolute amount
4. Investigate the root cause of significant variances
5. Document findings for financial reviews

## Using Scoped Views

1. Use the scope selector in the header
2. **Portfolio scope** — See aggregate financials across everything
3. **Company scope** — Focus on a single company's finances
4. **Project scope** — Detailed view for one project

## Financial Reporting

1. Review financial data at the desired scope level
2. Check that financial readiness scores are adequate
3. Use Reports module for formal financial reports
4. Export data as needed for external reporting`
  },
  {
    slug: 'finance-key-screens',
    title: 'Finance Key Screens',
    summary: 'Tour of the main Finance module screens and features.',
    category: 'finance',
    module: 'finance',
    audience: ['finance'],
    articleType: 'guide',
    tags: ['finance', 'screens', 'interface'],
    searchKeywords: ['finance screen', 'budget view', 'actuals page', 'finance dashboard', 'financial summary'],
    relatedArticles: ['finance-overview', 'finance-workflows'],
    lastUpdated: '2026-04-01',
    body: `## Finance Landing Page

The top-level finance view shows:
- **Summary cards** — Total revenue, costs, and net income
- **Company list** — All companies with financial summaries
- **Variance indicators** — Quick visual flags for budget deviations

## Company Finance View

Drilling into a company shows:
- **Company financial summary** — Aggregate metrics for all company projects
- **Project list** — Individual projects with financial status
- **Key financial metrics** — Revenue, costs, margins

## Site/Project Finance View

The project-level finance detail provides:
- **Budget vs Actual table** — Line-by-line comparison
- **Variance analysis** — Percentage and absolute differences
- **Financial readiness score** — Overall and by category
- **Time-series charts** — Revenue and cost trends over time
- **Period selection** — View monthly, quarterly, or annual data`
  },
  {
    slug: 'finance-troubleshooting',
    title: 'Finance Troubleshooting',
    summary: 'Common Finance module issues and solutions.',
    category: 'finance',
    module: 'finance',
    audience: ['finance'],
    articleType: 'troubleshooting',
    tags: ['finance', 'troubleshooting'],
    searchKeywords: ['finance problem', 'budget missing', 'actuals wrong', 'variance incorrect', 'readiness low'],
    relatedArticles: ['finance-overview', 'finance-readiness-explained', 'troubleshooting-missing-data'],
    lastUpdated: '2026-04-01',
    body: `## Financial Readiness Score Is Low

**Possible causes:**
- Budget data has not been entered for all line items
- Actual data is missing for recent periods
- Data quality issues with imported figures

**Solution:** Review the readiness breakdown to identify which categories are incomplete. Enter missing budget or actual data. See the Financial Readiness concept article for details.

## Budget and Actuals Don't Match Expected Periods

**Cause:** Budget and actual data may be entered for different time periods, causing misalignment.

**Solution:** Verify that budget and actual data cover the same time periods. Use the period selector to align the view.

## Variance Percentages Seem Wrong

**Possible causes:**
- Budget baseline may be zero or very small, causing large percentage swings
- Data may include partial periods
- Currency or unit mismatches

**Solution:** Check the underlying budget and actual values. Verify that both use the same currency and units. Large percentage variances on small absolute amounts are mathematically normal.

## Cannot Access Finance Module

**Cause:** Your role may not include Finance view permissions.

**Solution:** Contact your administrator to verify your role includes Finance module access.`
  }
];

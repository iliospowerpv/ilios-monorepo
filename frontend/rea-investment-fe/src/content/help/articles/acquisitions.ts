import { HelpArticle } from '../types';

export const acquisitionsArticles: HelpArticle[] = [
  {
    slug: 'acquisitions-overview',
    title: 'Acquisitions Module Overview',
    summary: 'Track and manage investment deals through the acquisition pipeline from initial screening to close.',
    category: 'acquisitions',
    module: 'acquisitions',
    audience: ['all-users', 'acquisitions'],
    articleType: 'overview',
    tags: ['acquisitions', 'deals', 'pipeline', 'overview'],
    searchKeywords: ['acquisitions', 'deals', 'pipeline', 'sales', 'opportunity', 'bid', 'prospect'],
    relatedArticles: [
      'acquisitions-workflows',
      'projects-vs-deals',
      'deal-to-project-conversion',
      'acquisitions-key-screens'
    ],
    lastUpdated: '2026-04-01',
    body: `## What Is the Acquisitions Module?

The **Acquisitions** module (formerly called Sales) is where your team tracks potential investment opportunities from first contact through to closing. It provides a pipeline view of all active deals and tools for managing the evaluation process.

## Key Features

### Deal Pipeline
View all deals organized by their current stage. The pipeline provides a visual overview of where each opportunity stands and its expected timeline.

### Deal Details
Each deal record includes:
- Project name and location
- Technology type (solar, wind, storage)
- Capacity and expected generation
- Financial projections
- Counterparty information
- Key dates and milestones
- Status and stage tracking

### Pipeline Stages
Deals progress through configurable stages:
1. **Screening** — Initial review of the opportunity
2. **Evaluation** — Detailed analysis and site assessment
3. **LOI (Letter of Intent)** — Formal expression of interest
4. **Under Contract** — Legal agreements in progress
5. **Due Diligence** — Final verification before closing
6. **Closed** — Deal completed and ready for conversion

### Filtering and Sorting
Filter the deal list by stage, technology type, company, capacity range, or custom tags. Sort by any column to prioritize your view.

## Who Uses It

- **Acquisitions/Business Development teams** — Primary users who manage the deal pipeline
- **Executives** — Review pipeline health and deal progress
- **Finance teams** — Evaluate financial projections on deals

## Important Terms

- **Deal** — A potential investment opportunity being evaluated
- **Pipeline** — The collection of all active deals and their stages
- **Stage** — The current phase of evaluation for a deal
- **Conversion** — The process of turning an approved deal into a managed project`
  },
  {
    slug: 'acquisitions-workflows',
    title: 'Acquisitions Workflows',
    summary:
      'Step-by-step guide to common acquisitions workflows including creating deals, advancing stages, and converting to projects.',
    category: 'acquisitions',
    module: 'acquisitions',
    audience: ['acquisitions'],
    articleType: 'tutorial',
    tags: ['acquisitions', 'workflow', 'deals', 'pipeline'],
    searchKeywords: ['create deal', 'new deal', 'advance stage', 'move deal', 'convert deal', 'close deal'],
    relatedArticles: ['acquisitions-overview', 'deal-to-project-conversion', 'projects-vs-deals'],
    lastUpdated: '2026-04-01',
    body: `## Creating a New Deal

1. Navigate to the **Acquisitions** module from the sidebar
2. Click the **New Deal** button
3. Fill in the required information:
   - Deal name
   - Technology type
   - Location
   - Estimated capacity
   - Counterparty
4. Set the initial pipeline stage (usually "Screening")
5. Click **Save** to create the deal

## Advancing a Deal Through Stages

As your evaluation progresses, move the deal to the next stage:

1. Open the deal detail page
2. Review the current stage requirements
3. Update the deal with any new information gathered
4. Change the stage to the next appropriate phase
5. Add notes documenting the reason for advancement

## Evaluating a Deal

During the evaluation phase:

1. Review financial projections and returns
2. Assess site characteristics and resource data
3. Check interconnection and permitting status
4. Evaluate counterparty and legal considerations
5. Document findings in the deal notes

## Closing and Converting a Deal

When a deal is approved for acquisition:

1. Update the deal status to "Closed"
2. Ensure all required fields are complete
3. Initiate the deal-to-project conversion process
4. Verify that project data is correctly migrated
5. The new project will appear in the Project Hub

## Managing the Pipeline View

- Use filters to focus on deals at specific stages
- Sort by expected close date to prioritize upcoming deadlines
- Export pipeline data for reporting and presentations
- Track pipeline metrics like total capacity under evaluation`
  },
  {
    slug: 'acquisitions-key-screens',
    title: 'Acquisitions Key Screens',
    summary: 'A tour of the main screens and views available in the Acquisitions module.',
    category: 'acquisitions',
    module: 'acquisitions',
    audience: ['acquisitions'],
    articleType: 'guide',
    tags: ['acquisitions', 'screens', 'interface', 'UI'],
    searchKeywords: ['acquisitions screen', 'deal list', 'pipeline view', 'deal detail', 'acquisitions page'],
    relatedArticles: ['acquisitions-overview', 'acquisitions-workflows'],
    lastUpdated: '2026-04-01',
    body: `## Pipeline Home

The main Acquisitions page shows your deal pipeline with:

- **Summary cards** — Count of deals by stage with total capacity
- **Deal table** — Sortable, filterable list of all deals
- **Scope selector** — Switch between portfolio, company, or project-level views

## Deal Detail Page

Clicking on a deal opens its detail page with:

- **Header** — Deal name, stage badge, and key metrics
- **Details section** — All deal fields organized by category
- **Timeline** — History of stage changes and updates
- **Notes** — Team comments and observations
- **Documents** — Attached files related to the deal

## Filtering and Search

The deal list supports:

- **Stage filter** — Show deals at specific pipeline stages
- **Technology filter** — Filter by solar, wind, or storage
- **Company filter** — Show deals for specific companies
- **Text search** — Search by deal name or description
- **Date range** — Filter by expected close date`
  },
  {
    slug: 'acquisitions-troubleshooting',
    title: 'Acquisitions Troubleshooting',
    summary: 'Common issues and solutions when working with the Acquisitions module.',
    category: 'acquisitions',
    module: 'acquisitions',
    audience: ['acquisitions'],
    articleType: 'troubleshooting',
    tags: ['acquisitions', 'troubleshooting', 'issues'],
    searchKeywords: ['acquisitions problem', 'deal not showing', 'cannot create deal', 'pipeline empty'],
    relatedArticles: ['acquisitions-overview', 'troubleshooting-permissions', 'troubleshooting-missing-data'],
    lastUpdated: '2026-04-01',
    body: `## I Can't See the Acquisitions Module

**Cause:** Your role may not include Acquisitions or Sales view permissions.

**Solution:** Contact your administrator to verify your role includes Acquisitions access.

## Deals Are Not Showing in the Pipeline

**Possible causes:**
- Active filters may be hiding deals — check and clear any filters
- You may be viewing a scoped view (company-level) that doesn't include those deals
- The deals may have been archived or deleted

**Solution:** Reset all filters and switch to the portfolio-level view to see all deals.

## I Can't Create New Deals

**Cause:** Your role may only have view permissions for Acquisitions, not edit permissions.

**Solution:** Contact your administrator to request edit access to the Acquisitions module.

## Deal Stage Won't Advance

**Possible causes:**
- Required fields for the next stage may not be filled in
- You may not have edit permissions

**Solution:** Review the deal details for any missing required information, then try advancing the stage again.`
  }
];

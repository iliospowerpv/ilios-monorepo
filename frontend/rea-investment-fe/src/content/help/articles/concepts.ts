import { HelpArticle } from '../types';

export const conceptArticles: HelpArticle[] = [
  {
    slug: 'finance-readiness-explained',
    title: 'Finance Readiness Explained',
    summary: 'How the financial readiness scoring system works and what it means for your projects.',
    category: 'concepts',
    audience: ['finance', 'asset-manager'],
    articleType: 'concept',
    tags: ['finance', 'readiness', 'scoring', 'data quality'],
    searchKeywords: ['finance readiness', 'readiness score', 'financial readiness', 'data completeness', 'score'],
    relatedArticles: ['finance-overview', 'budget-vs-actual-explained', 'kpi-definitions'],
    lastUpdated: '2026-04-01',
    body: `## What Is Financial Readiness?

**Financial readiness** is a scoring system in Ilios that evaluates how complete and reliable a project's financial data is. It helps teams understand whether financial figures are trustworthy enough for reporting, decision-making, and investor communications.

## How the Score Is Calculated

The readiness score considers several dimensions:

### Budget Completeness
- Are all budget line items entered?
- Do budgets cover the full reporting period?
- Are budget figures reasonable and internally consistent?

### Actuals Timeliness
- Are actual figures entered for recent periods?
- How current is the latest actuals data?
- Are there gaps in the actuals timeline?

### Data Quality
- Do budget and actual figures use consistent categories?
- Are there obvious data entry errors (negative values, extreme outliers)?
- Are all required financial fields populated?

### Documentation
- Are supporting documents uploaded for key financial items?
- Are variance explanations provided for significant deviations?

## Score Ranges

| Score Range | Status | Meaning |
|-------------|--------|---------|
| 90-100% | Excellent | Data is complete and current |
| 70-89% | Good | Minor gaps that should be addressed |
| 50-69% | Needs Attention | Significant gaps affecting reliability |
| Below 50% | Incomplete | Major data missing, not ready for reporting |

## Why It Matters

Financial readiness affects:
- **Reporting confidence** — Higher readiness means more reliable reports
- **Decision-making** — Ensures decisions are based on complete data
- **Investor relations** — Demonstrates data governance and professionalism
- **Audit preparedness** — Reduces risk of audit findings

## Improving Your Score

1. Enter budget data for all line items and periods
2. Keep actuals data current (update monthly at minimum)
3. Document explanations for significant variances
4. Upload supporting documents for major financial items
5. Review and correct any data quality issues flagged by the system`
  },
  {
    slug: 'diligence-workflows-explained',
    title: 'Diligence Workflows Explained',
    summary: 'How the due diligence process works in Ilios, from document collection through completion tracking.',
    category: 'concepts',
    audience: ['all-users', 'acquisitions'],
    articleType: 'concept',
    tags: ['diligence', 'due-diligence', 'workflow', 'documents', 'data-room'],
    searchKeywords: ['due diligence', 'diligence workflow', 'document checklist', 'diligence process', 'verification'],
    relatedArticles: ['data-room-overview', 'acquisitions-overview', 'projects-vs-deals'],
    lastUpdated: '2026-04-01',
    body: `## What Is Due Diligence?

**Due diligence** is the investigation and verification process that occurs before acquiring a renewable energy project. In Ilios, the diligence workflow is supported through the Data Room and Due Diligence modules.

## The Diligence Process

### 1. Document Collection
The first phase involves gathering all relevant project documents:
- Engineering reports and studies
- Environmental assessments
- Permitting documents
- Financial projections and models
- Legal agreements and contracts
- Insurance certificates
- Land and interconnection agreements

### 2. Categorization and Organization
Documents are organized into the Data Room using predefined categories that align with industry-standard diligence checklists. Each category has:
- Required documents
- Optional supporting materials
- Status tracking (complete/incomplete)

### 3. Review and Verification
Team members review uploaded documents to verify:
- Document authenticity and currency
- Completeness of information
- Consistency with other data sources
- Compliance with requirements

### 4. Completion Tracking
Ilios tracks the overall diligence completion status:
- Category-by-category progress
- Overall readiness percentage
- Outstanding items list
- Blocking issues identification

### 5. Sign-Off
When diligence is complete, the process culminates in:
- Final review of all categories
- Resolution of outstanding items
- Formal sign-off by relevant stakeholders
- Deal advancement to closing

## Best Practices

- Start document collection early in the deal process
- Use the Data Room category structure as your checklist
- Track progress regularly and follow up on missing items
- Document any exceptions or waivers for incomplete categories
- Maintain version control for documents that get updated during diligence`
  },
  {
    slug: 'o-and-m-performance-explained',
    title: 'O&M Performance Metrics Explained',
    summary: 'Understanding availability, performance ratio, and other key O&M metrics used in Ilios.',
    category: 'concepts',
    audience: ['operations', 'asset-manager'],
    articleType: 'concept',
    tags: ['o-and-m', 'performance', 'availability', 'PR', 'metrics'],
    searchKeywords: [
      'availability',
      'performance ratio',
      'PR',
      'generation',
      'capacity factor',
      'o&m metrics',
      'uptime'
    ],
    relatedArticles: ['o-and-m-overview', 'kpi-definitions', 'portfolio-rollups-explained'],
    lastUpdated: '2026-04-01',
    body: `## Key O&M Metrics

### Availability
**Availability** measures the percentage of time that a system or device is operational and capable of generating energy. It is one of the most important O&M metrics.

**Calculation:**
\`Availability = (Total Hours - Downtime Hours) / Total Hours × 100%\`

**Types of availability:**
- **Time-based availability** — Simple uptime vs downtime ratio
- **Energy-based availability** — Weighted by the energy that could have been produced during downtime

**Target:** Most solar projects target 97-99% availability.

### Performance Ratio (PR)
**Performance ratio** measures how effectively a solar installation converts sunlight into electricity, accounting for all losses.

**Calculation:**
\`PR = Actual Energy Output / (Reference Irradiance × Installed Capacity) × 100%\`

**Factors affecting PR:**
- Temperature losses
- Shading
- Soiling (dirt, dust, snow)
- Wiring and conversion losses
- Inverter efficiency
- Equipment degradation

**Target:** Typical PR ranges from 75-85% depending on climate and technology.

### Generation (kWh/MWh)
The total energy produced by a site or device over a given period. Compared against:
- **Expected generation** — Based on resource data and system modeling
- **Budget generation** — The financial plan's assumed output
- **Historical generation** — Previous periods for trend analysis

### Capacity Factor
The ratio of actual energy output to the maximum possible output if the system ran at full capacity continuously.

\`Capacity Factor = Actual Output / (Installed Capacity × Hours in Period) × 100%\`

## How Metrics Roll Up

Site-level metrics aggregate to company and portfolio levels:
- **Availability** — Capacity-weighted average across sites
- **PR** — Capacity-weighted average
- **Generation** — Sum of all site generation
- **Capacity Factor** — Weighted by installed capacity

## Common Metric Issues

- **Low availability** — Usually indicates equipment failures or communication outages
- **Low PR** — May indicate soiling, shading, degradation, or modeling issues
- **Generation shortfall** — Could be weather-related or equipment-related
- **Data gaps** — Missing telemetry data can distort calculated metrics`
  },
  {
    slug: 'portfolio-rollups-explained',
    title: 'Portfolio Rollups Explained',
    summary: 'How Ilios aggregates data from project level up to company and portfolio levels.',
    category: 'concepts',
    audience: ['all-users', 'executive'],
    articleType: 'concept',
    tags: ['portfolio', 'rollups', 'aggregation', 'hierarchy'],
    searchKeywords: ['rollup', 'aggregate', 'portfolio level', 'summary', 'totals', 'company level', 'roll up'],
    relatedArticles: ['portfolio-company-project-hierarchy', 'reports-overview', 'kpi-definitions'],
    lastUpdated: '2026-04-01',
    body: `## What Are Portfolio Rollups?

**Rollups** are the process of aggregating data from individual projects up through companies to the portfolio level. They allow you to see summary metrics at any level of the organizational hierarchy.

## How Rollups Work

### Project → Company
Project-level data is aggregated to the company level:
- **Financial data** — Summed (revenue, costs, budgets)
- **Capacity** — Summed
- **Performance metrics** — Capacity-weighted averages (availability, PR)
- **Counts** — Summed (tasks, alerts, documents)

### Company → Portfolio
Company-level aggregates are further rolled up to portfolio level using the same methods.

## Aggregation Methods

Different metrics use different aggregation approaches:

| Metric Type | Method | Example |
|------------|--------|---------|
| Financial amounts | Sum | Total revenue across all projects |
| Capacity | Sum | Total installed MW |
| Percentages/Ratios | Weighted average | Availability weighted by capacity |
| Counts | Sum | Total number of open tasks |
| Dates | Min/Max | Earliest COD, latest update |
| Status | Mode or worst-case | Most common status, or most critical alert |

## Where Rollups Appear

Rollups are used throughout Ilios:
- **Home module** — Portfolio summary metrics
- **Finance** — Financial summaries at each level
- **O&M** — Performance aggregates
- **Reports** — Portfolio-wide analytics
- **Project Hub** — Portfolio and company overviews

## Important Considerations

- Rollups may not refresh in real-time; there may be a short delay
- Rollup calculations only include projects you have permission to view
- Some metrics may show "N/A" if insufficient data exists for a meaningful aggregate
- Currency differences between projects may affect financial rollups`
  },
  {
    slug: 'budget-vs-actual-explained',
    title: 'Budget vs Actual Analysis',
    summary: 'Understanding how Ilios compares planned budgets against actual financial performance.',
    category: 'concepts',
    audience: ['finance', 'asset-manager'],
    articleType: 'concept',
    tags: ['finance', 'budget', 'actuals', 'variance', 'analysis'],
    searchKeywords: ['budget', 'actual', 'variance', 'comparison', 'budget vs actual', 'over budget', 'under budget'],
    relatedArticles: ['finance-overview', 'finance-readiness-explained', 'kpi-definitions'],
    lastUpdated: '2026-04-01',
    body: `## What Is Budget vs Actual Analysis?

**Budget vs actual** (BvA) analysis compares your planned financial figures (the budget) against what actually happened (the actuals). This comparison reveals variances — areas where reality differs from the plan.

## Key Concepts

### Budget
The **budget** represents planned financial figures, typically set at the beginning of a period. It includes:
- Expected revenue (energy sales, capacity payments, incentives)
- Planned operating expenses
- Capital expenditure plans
- Debt service schedules

### Actuals
**Actuals** are the real financial figures recorded during or after a period:
- Actual revenue received
- Actual costs incurred
- Real cash flows

### Variance
The **variance** is the difference between budget and actual:
\`Variance = Actual - Budget\`

- **Positive variance** on revenue = better than planned (favorable)
- **Negative variance** on revenue = worse than planned (unfavorable)
- **Positive variance** on costs = higher than planned (unfavorable)
- **Negative variance** on costs = lower than planned (favorable)

## How It Works in Ilios

### Line-Item Comparison
The Finance module shows budget and actual values side-by-side for each financial line item, with the variance calculated automatically.

### Variance Indicators
Visual indicators highlight significant variances:
- Green = favorable variance
- Red = unfavorable variance
- The threshold for "significant" can be configured

### Period Alignment
Budget and actual data must cover the same time period for meaningful comparison. Ilios supports:
- Monthly comparisons
- Quarterly rollups
- Annual summaries
- Year-to-date views

## Best Practices

1. Enter budget data before the period begins
2. Update actuals as soon as data is available (monthly recommended)
3. Investigate variances exceeding 10% of budget
4. Document explanations for significant variances
5. Use variance trends to improve future budgeting`
  },
  {
    slug: 'asset-hierarchy-explained',
    title: 'Asset Hierarchy Explained',
    summary: 'How physical assets (sites, devices, components) are organized within the Ilios platform.',
    category: 'concepts',
    audience: ['operations', 'asset-manager'],
    articleType: 'concept',
    tags: ['assets', 'hierarchy', 'devices', 'components', 'organization'],
    searchKeywords: ['asset hierarchy', 'device', 'inverter', 'meter', 'component', 'equipment', 'asset structure'],
    relatedArticles: ['portfolio-company-project-hierarchy', 'o-and-m-overview', 'project-hub-overview'],
    lastUpdated: '2026-04-01',
    body: `## The Asset Hierarchy

Within each project, Ilios organizes physical equipment in a hierarchical structure:

### Site / Project (Top)
The physical location where the renewable energy installation exists. Contains:
- Geographic coordinates and address
- Total installed capacity
- Technology type (solar, wind, storage)
- Interconnection point

### Device Level
Devices are the major pieces of equipment at a site:
- **Inverters** — Convert DC to AC power
- **Meters** — Measure energy production and consumption
- **Weather stations** — Monitor irradiance, temperature, wind
- **Transformers** — Step up voltage for grid connection
- **Trackers** — Adjust panel orientation (for tracking systems)

### Component Level
Components are sub-elements of devices (where tracked):
- Individual solar panels or strings
- Battery cells or modules
- Turbine blades or gearboxes

## How the Hierarchy Is Used

### O&M Monitoring
Performance metrics can be viewed at each level:
- Site-level aggregate performance
- Device-level individual performance
- Alerts generated at the device level roll up to site level

### Telemetry Data
Data flows from devices up through the hierarchy:
- Device sensors report raw telemetry
- Site-level metrics are calculated from device data
- Portfolio metrics are aggregated from site data

### Maintenance Tracking
Work orders can reference specific levels:
- Site-level maintenance (grounds keeping, security)
- Device-level repairs (inverter replacement)
- Component-level work (panel cleaning, string repair)

## Viewing the Hierarchy

The asset hierarchy is visible in:
- **Project Hub** — Project overview shows site details
- **O&M Module** — Device list and telemetry views
- **Telemetry Page** — Detailed device-level data exploration`
  },
  {
    slug: 'deal-to-project-conversion',
    title: 'Deal to Project Conversion',
    summary: 'How deals in the Acquisitions pipeline are converted into managed projects in the Project Hub.',
    category: 'concepts',
    audience: ['acquisitions', 'asset-manager', 'admin'],
    articleType: 'concept',
    tags: ['deals', 'projects', 'conversion', 'acquisitions', 'workflow'],
    searchKeywords: ['convert deal', 'deal to project', 'conversion', 'close deal', 'create project from deal'],
    relatedArticles: ['projects-vs-deals', 'acquisitions-overview', 'project-hub-overview', 'lifecycle-stages'],
    lastUpdated: '2026-04-01',
    body: `## Overview

When a deal successfully completes the acquisitions pipeline, it needs to be converted into a project for ongoing management. This conversion process transfers key information from the deal record to a new project in the Project Hub.

## When to Convert

A deal is typically ready for conversion when:
- The acquisition has closed
- Due diligence is complete
- Financial terms are finalized
- All parties have signed the necessary agreements

## What Gets Transferred

During conversion, key data migrates from the deal to the project:

| Deal Data | Project Field |
|-----------|---------------|
| Deal name | Project name |
| Location | Site location |
| Capacity | Installed capacity |
| Technology | Technology type |
| Financial projections | Initial budget |
| Documents | Data Room content |

## The Conversion Process

1. An administrator or acquisitions lead initiates conversion
2. The system creates a new project record
3. Deal data is mapped to project fields
4. Documents are migrated to the project's Data Room
5. The project's lifecycle stage is set (typically "Development" or "Pre-Construction")
6. The deal is marked as "Converted" in Acquisitions

## After Conversion

Once converted:
- The project appears in the **Project Hub**
- All project modules become available based on lifecycle stage
- The original deal record is preserved in Acquisitions for historical reference
- Additional project details can be filled in as needed

## Important Notes

- Conversion does not delete the original deal record
- Not all deal fields have direct project equivalents — some data may need manual entry
- The conversion is a one-way process; projects cannot be "unconverted" back to deals`
  }
];

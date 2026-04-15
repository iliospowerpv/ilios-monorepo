import { HelpArticle } from '../types';

export const referenceArticles: HelpArticle[] = [
  {
    slug: 'field-definitions',
    title: 'Field Definitions Reference',
    summary: 'Complete reference of key data fields used throughout the Ilios platform.',
    category: 'reference',
    audience: ['all-users'],
    articleType: 'reference',
    tags: ['fields', 'definitions', 'reference', 'data'],
    searchKeywords: ['field', 'definition', 'column', 'data field', 'what is', 'meaning'],
    relatedArticles: ['kpi-definitions', 'status-definitions', 'lifecycle-states-reference'],
    lastUpdated: '2026-04-01',
    body: `## Project Fields

| Field | Description | Where Used |
|-------|-------------|------------|
| Project Name | The display name for the project/site | Project Hub, all modules |
| Capacity (MW) | The installed nameplate capacity in megawatts | Project Hub, O&M, Reports |
| Technology | The generation technology (Solar PV, Wind, Storage) | Project Hub, Acquisitions |
| Location | Geographic coordinates and address of the site | Project Hub, O&M |
| COD (Commercial Operation Date) | The date the project began commercial operations | Project Hub, Finance |
| Lifecycle Stage | Current phase of the project's lifecycle | Project Hub, Portfolio Admin |
| Company | The legal entity that owns the project | All modules |

## Financial Fields

| Field | Description | Where Used |
|-------|-------------|------------|
| Budget | Planned financial figure for a given period and line item | Finance |
| Actuals | Recorded financial figure for a given period | Finance |
| Variance | Difference between actual and budget (Actual - Budget) | Finance |
| Variance % | Variance as a percentage of budget | Finance |
| Revenue | Income from energy sales and other sources | Finance, Reports |
| OPEX | Operating expenses for the project | Finance |
| CAPEX | Capital expenditures for construction or improvements | Finance |
| Net Income | Revenue minus total expenses | Finance, Reports |

## O&M Fields

| Field | Description | Where Used |
|-------|-------------|------------|
| Availability (%) | Percentage of time the system was operational | O&M, Reports |
| Performance Ratio (%) | Ratio of actual to theoretical energy output | O&M, Reports |
| Generation (kWh/MWh) | Total energy produced in the period | O&M, Reports |
| Irradiance (kWh/m²) | Solar energy received per unit area | O&M |
| Device Status | Current operational state of a device | O&M |
| Alert Severity | Criticality level of an O&M alert | O&M |

## Deal Fields

| Field | Description | Where Used |
|-------|-------------|------------|
| Deal Name | Name of the acquisition opportunity | Acquisitions |
| Pipeline Stage | Current evaluation phase of the deal | Acquisitions |
| Expected Capacity | Estimated capacity if acquired | Acquisitions |
| Expected Close Date | Projected date for deal closure | Acquisitions |
| Technology Type | Type of renewable energy project | Acquisitions |
| Counterparty | The selling party or development partner | Acquisitions |

## Task Fields

| Field | Description | Where Used |
|-------|-------------|------------|
| Task Title | Short description of the work item | Tasks |
| Priority | Urgency level (Low, Medium, High, Critical) | Tasks |
| Status | Current state (Open, In Progress, Done) | Tasks |
| Assignee | Person responsible for the task | Tasks |
| Due Date | Deadline for task completion | Tasks |`
  },
  {
    slug: 'kpi-definitions',
    title: 'KPI Definitions',
    summary: 'Definitions and calculation methods for all key performance indicators used in Ilios.',
    category: 'reference',
    audience: ['all-users'],
    articleType: 'reference',
    tags: ['KPI', 'metrics', 'performance', 'definitions'],
    searchKeywords: ['KPI', 'metric', 'key performance indicator', 'calculation', 'formula', 'how calculated'],
    relatedArticles: ['field-definitions', 'o-and-m-performance-explained', 'portfolio-rollups-explained'],
    lastUpdated: '2026-04-01',
    body: `## Operational KPIs

### Availability
- **Definition:** Percentage of time equipment is operational and capable of producing energy
- **Formula:** \`(Total Hours - Downtime) / Total Hours × 100\`
- **Unit:** Percentage (%)
- **Target:** 97-99% for solar, 95-97% for wind
- **Used in:** O&M, Reports, Home

### Performance Ratio (PR)
- **Definition:** Effectiveness of converting available sunlight into electricity
- **Formula:** \`Actual Output / (Irradiance × Capacity × Hours) × 100\`
- **Unit:** Percentage (%)
- **Target:** 75-85% depending on climate
- **Used in:** O&M, Reports

### Capacity Factor
- **Definition:** Actual output vs maximum theoretical output
- **Formula:** \`Actual Output / (Capacity × Hours in Period) × 100\`
- **Unit:** Percentage (%)
- **Used in:** O&M, Reports

### Specific Yield
- **Definition:** Energy produced per unit of installed capacity
- **Formula:** \`Total Generation / Installed Capacity\`
- **Unit:** kWh/kWp
- **Used in:** O&M, Reports

## Financial KPIs

### Revenue per MW
- **Definition:** Revenue normalized by installed capacity
- **Formula:** \`Total Revenue / Installed Capacity (MW)\`
- **Unit:** Currency/MW
- **Used in:** Finance, Reports

### Operating Expense Ratio
- **Definition:** Operating costs as a percentage of revenue
- **Formula:** \`Total OPEX / Total Revenue × 100\`
- **Unit:** Percentage (%)
- **Used in:** Finance

### Budget Variance
- **Definition:** Deviation of actuals from budget
- **Formula:** \`(Actual - Budget) / Budget × 100\`
- **Unit:** Percentage (%)
- **Used in:** Finance

### Financial Readiness Score
- **Definition:** Completeness and quality of financial data
- **Calculation:** Composite score based on budget completeness, actuals timeliness, and data quality
- **Unit:** Percentage (%)
- **Used in:** Finance

## Portfolio KPIs

### Total Installed Capacity
- **Definition:** Sum of all project capacities
- **Unit:** MW
- **Used in:** Home, Reports, Portfolio

### Total Generation
- **Definition:** Sum of energy produced across all projects
- **Unit:** MWh
- **Used in:** Home, Reports

### Portfolio Availability
- **Definition:** Capacity-weighted average availability across all projects
- **Unit:** Percentage (%)
- **Used in:** Home, Reports`
  },
  {
    slug: 'status-definitions',
    title: 'Status Definitions',
    summary: 'Reference for all status values used across the Ilios platform.',
    category: 'reference',
    audience: ['all-users'],
    articleType: 'reference',
    tags: ['status', 'definitions', 'reference', 'states'],
    searchKeywords: ['status', 'state', 'what means', 'status meaning', 'open', 'closed', 'active', 'inactive'],
    relatedArticles: ['field-definitions', 'lifecycle-states-reference'],
    lastUpdated: '2026-04-01',
    body: `## Deal Statuses

| Status | Meaning |
|--------|---------|
| Screening | Deal is in initial review |
| Evaluation | Detailed analysis in progress |
| LOI | Letter of Intent stage |
| Under Contract | Legal agreements being finalized |
| Due Diligence | Final verification before close |
| Closed Won | Deal successfully acquired |
| Closed Lost | Deal was not pursued or lost |
| On Hold | Deal temporarily paused |

## Task Statuses

| Status | Meaning |
|--------|---------|
| Open | Task created but not yet started |
| In Progress | Work is actively being done |
| Blocked | Task cannot proceed due to a dependency |
| Done | Task has been completed |
| Cancelled | Task was cancelled and will not be completed |

## Device Statuses

| Status | Meaning |
|--------|---------|
| Online | Device is communicating and operating normally |
| Offline | Device is not communicating |
| Warning | Device is operating but with performance issues |
| Error | Device has a fault condition |
| Maintenance | Device is down for planned maintenance |

## Alert Severities

| Severity | Meaning | Response |
|----------|---------|----------|
| Critical | Severe issue requiring immediate attention | Respond within hours |
| Warning | Significant issue that should be addressed soon | Respond within 1-2 days |
| Info | Informational alert, no immediate action needed | Review during routine check |

## Document Statuses

| Status | Meaning |
|--------|---------|
| Draft | Document uploaded but not yet reviewed |
| Under Review | Document is being evaluated |
| Approved | Document has been reviewed and accepted |
| Rejected | Document was reviewed and not accepted |
| Expired | Document has passed its validity date |`
  },
  {
    slug: 'lifecycle-states-reference',
    title: 'Lifecycle States Reference',
    summary: 'Complete reference of all project lifecycle states and their implications.',
    category: 'reference',
    audience: ['all-users', 'admin'],
    articleType: 'reference',
    tags: ['lifecycle', 'states', 'reference', 'stages'],
    searchKeywords: ['lifecycle state', 'project stage', 'development', 'construction', 'operations', 'COD', 'NTP'],
    relatedArticles: ['lifecycle-stages', 'module-activation', 'status-definitions'],
    lastUpdated: '2026-04-01',
    body: `## Lifecycle States

| State | Description | Typical Duration | Key Activities |
|-------|-------------|------------------|----------------|
| Development | Early planning and assessment | 6-24 months | Site assessment, permitting, engineering |
| Pre-Construction | Final preparation before building | 1-6 months | Procurement, financing, final permits |
| Construction | Active building phase | 3-18 months | Equipment installation, civil works |
| Commissioning | Testing and validation | 1-3 months | System testing, performance verification |
| NTP | Notice to Proceed milestone | Point-in-time | Formal authorization to commence operations |
| COD | Commercial Operation Date | Point-in-time | Beginning of commercial energy production |
| Operations | Active energy production | 20-35 years | Monitoring, maintenance, financial tracking |
| Decommissioning | End-of-life retirement | 6-18 months | Equipment removal, site restoration |

## Module Availability by State

| Module | Dev | Pre-Con | Const | Comm | Ops | Decom |
|--------|-----|---------|-------|------|-----|-------|
| Home | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Acquisitions | ✓ | — | — | — | — | — |
| Project Hub | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| Data Room | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| O&M | — | — | — | ✓ | ✓ | — |
| Finance | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| Tasks | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| Reports | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| Portfolio Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

## State Transitions

Typical transitions follow a linear progression, though some projects may skip stages:

\`Development → Pre-Construction → Construction → Commissioning → NTP → COD → Operations → Decommissioning\`

State transitions are managed through Portfolio Admin and may trigger:
- Module activation/deactivation
- Notification to relevant users
- Automated workflow updates`
  },
  {
    slug: 'role-behavior-reference',
    title: 'Role Behavior Reference',
    summary: 'How different user roles interact with the Ilios platform and what capabilities each role provides.',
    category: 'reference',
    audience: ['admin'],
    articleType: 'reference',
    tags: ['roles', 'permissions', 'behavior', 'access'],
    searchKeywords: ['role', 'permission', 'access', 'what can', 'capability', 'user type', 'admin role'],
    relatedArticles: ['permissions-and-access', 'portfolio-admin-overview'],
    lastUpdated: '2026-04-01',
    body: `## Role Structure

Each role in Ilios defines permissions across all modules. Permissions operate at two levels:

### View Permission
Allows the user to:
- See the module in the sidebar navigation
- Access the module's pages
- View data, reports, and dashboards
- Export data where supported

### Edit Permission
Allows the user to (in addition to view):
- Create new records
- Modify existing data
- Delete records where allowed
- Perform administrative actions within the module

## Module-Level Permissions

| Permission Key | Controls Access To |
|---------------|-------------------|
| Acquisitions | Acquisitions module, deal management |
| Sales | Legacy key, same as Acquisitions |
| Project Hub | Project Hub module, project management |
| Asset Management | Legacy key, same as Project Hub |
| O&M (Production Monitoring) | O&M module, device monitoring |
| Finance | Finance module, financial data |
| Reports | Reports module, portfolio analytics |
| Settings Page | Portfolio Admin and settings |
| Investor Dashboard | Portfolio/investor view |

## Special User Types

### System User
- Has access to all modules regardless of role permissions
- Can access system-level settings and health checks
- Used for platform administrators

### Company Admin
- Has elevated access within their assigned companies
- Can manage company-level settings
- Role includes Settings Page view permission

## Permission Evaluation

When a user tries to access a module, the system checks:

1. Is the user a system user? → Grant access
2. Does the user's role have view permission for this module? → Grant access
3. Neither? → Show "You don't have permission" and disable the module`
  }
];

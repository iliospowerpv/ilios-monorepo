import { GlossaryEntry } from './types';

export const glossaryEntries: GlossaryEntry[] = [
  {
    term: 'Actuals',
    slug: 'actuals',
    definition:
      'Real financial figures recorded during or after an operating period, as opposed to budgeted or projected figures. Actuals include actual revenue received and actual costs incurred.',
    relatedTerms: ['Budget', 'Variance'],
    tags: ['finance']
  },
  {
    term: 'Asset',
    slug: 'asset',
    definition:
      'A renewable energy installation or project, such as a solar farm or wind park. Used interchangeably with "project" or "site" in Ilios.',
    relatedTerms: ['Project', 'Site'],
    tags: ['general']
  },
  {
    term: 'Availability',
    slug: 'availability',
    definition:
      'The percentage of time that a device or site is operational and capable of generating energy. Calculated as (Total Hours - Downtime) / Total Hours × 100%.',
    relatedTerms: ['Performance Ratio', 'Downtime'],
    tags: ['o&m', 'metrics']
  },
  {
    term: 'Budget',
    slug: 'budget',
    definition:
      'Planned financial figures for a given period, including expected revenue, operating expenses, and capital expenditures. Budgets serve as the baseline for variance analysis.',
    relatedTerms: ['Actuals', 'Variance'],
    tags: ['finance']
  },
  {
    term: 'Capacity (MW)',
    slug: 'capacity',
    definition:
      'The nameplate capacity of a renewable energy installation measured in megawatts (MW). Represents the maximum power output under standard conditions.',
    relatedTerms: ['Generation', 'Capacity Factor'],
    tags: ['general', 'metrics']
  },
  {
    term: 'Capacity Factor',
    slug: 'capacity-factor',
    definition:
      'The ratio of actual energy output to the maximum possible output if the system ran at full capacity continuously. Expressed as a percentage.',
    relatedTerms: ['Capacity (MW)', 'Generation'],
    tags: ['o&m', 'metrics']
  },
  {
    term: 'COD (Commercial Operation Date)',
    slug: 'cod',
    definition:
      'The date when a project begins commercial energy production. This is a critical financial milestone that triggers revenue recognition, warranty periods, and performance guarantees.',
    relatedTerms: ['NTP', 'Lifecycle Stage'],
    tags: ['lifecycle', 'finance']
  },
  {
    term: 'Company',
    slug: 'company',
    definition:
      'A legal entity, special purpose vehicle (SPV), or subsidiary that owns one or more projects in Ilios. Companies sit at the middle level of the portfolio hierarchy.',
    relatedTerms: ['Portfolio', 'Project'],
    tags: ['hierarchy']
  },
  {
    term: 'Data Room',
    slug: 'data-room',
    definition:
      'A secure document management space within Ilios for organizing, storing, and tracking project documents. Used extensively during due diligence and ongoing document management.',
    relatedTerms: ['Due Diligence', 'Document'],
    tags: ['modules']
  },
  {
    term: 'Deal',
    slug: 'deal',
    definition:
      'A potential investment opportunity being evaluated in the Acquisitions pipeline. Deals progress through evaluation stages and may be converted to projects upon acquisition.',
    relatedTerms: ['Project', 'Pipeline'],
    tags: ['acquisitions']
  },
  {
    term: 'Diligence',
    slug: 'diligence',
    definition:
      'Short for "due diligence" — the investigation and verification process conducted before acquiring a project. Includes reviewing documents, financial projections, legal agreements, and site assessments.',
    relatedTerms: ['Data Room', 'Deal'],
    tags: ['acquisitions']
  },
  {
    term: 'Downtime',
    slug: 'downtime',
    definition:
      'Periods when equipment is not operational, whether due to equipment failure, maintenance, grid issues, or other causes. Downtime reduces availability metrics.',
    relatedTerms: ['Availability', 'Work Order'],
    tags: ['o&m']
  },
  {
    term: 'Finance Readiness',
    slug: 'finance-readiness',
    definition:
      "A scoring system that evaluates the completeness, timeliness, and quality of a project's financial data. Higher scores indicate more reliable data for reporting and decision-making.",
    relatedTerms: ['Budget', 'Actuals'],
    tags: ['finance']
  },
  {
    term: 'Generation',
    slug: 'generation',
    definition:
      'The total energy produced by a renewable energy installation over a given period, typically measured in kilowatt-hours (kWh) or megawatt-hours (MWh).',
    relatedTerms: ['Capacity (MW)', 'Performance Ratio'],
    tags: ['o&m', 'metrics']
  },
  {
    term: 'Inverter',
    slug: 'inverter',
    definition:
      'A device that converts direct current (DC) electricity from solar panels or batteries to alternating current (AC) for grid connection. Inverters are key monitoring points in O&M.',
    relatedTerms: ['Device', 'Telemetry'],
    tags: ['o&m', 'equipment']
  },
  {
    term: 'Irradiance',
    slug: 'irradiance',
    definition:
      'The amount of solar energy received per unit area, typically measured in kWh/m². Irradiance data is used to calculate expected generation and performance ratio.',
    relatedTerms: ['Performance Ratio', 'Generation'],
    tags: ['o&m', 'metrics']
  },
  {
    term: 'KPI (Key Performance Indicator)',
    slug: 'kpi',
    definition:
      'A measurable value that demonstrates how effectively a project or portfolio is performing. Common KPIs in Ilios include availability, performance ratio, and financial readiness.',
    relatedTerms: ['Availability', 'Performance Ratio'],
    tags: ['metrics']
  },
  {
    term: 'Lifecycle Stage',
    slug: 'lifecycle-stage',
    definition:
      "The current phase of a project's journey from development through operations. Stages include Development, Pre-Construction, Construction, Commissioning, NTP, COD, Operations, and Decommissioning.",
    relatedTerms: ['COD', 'NTP'],
    tags: ['lifecycle']
  },
  {
    term: 'NTP (Notice to Proceed)',
    slug: 'ntp',
    definition:
      'A formal milestone indicating that all conditions have been met for a project to begin construction or operations. Often triggers financial obligations and starts warranty periods.',
    relatedTerms: ['COD', 'Lifecycle Stage'],
    tags: ['lifecycle']
  },
  {
    term: 'Performance Ratio (PR)',
    slug: 'performance-ratio',
    definition:
      'A metric that measures how effectively a solar installation converts available sunlight into electricity, accounting for all system losses. Expressed as a percentage, typically 75-85%.',
    relatedTerms: ['Availability', 'Irradiance'],
    tags: ['o&m', 'metrics']
  },
  {
    term: 'Pipeline',
    slug: 'pipeline',
    definition:
      'The collection of all active deals in the Acquisitions module, organized by their evaluation stage. The pipeline view provides a visual overview of deal flow.',
    relatedTerms: ['Deal', 'Acquisitions'],
    tags: ['acquisitions']
  },
  {
    term: 'Portfolio',
    slug: 'portfolio',
    definition:
      'The top level of the Ilios hierarchy, representing the entire collection of investments managed through the platform. Portfolio-level views show aggregate metrics across all companies and projects.',
    relatedTerms: ['Company', 'Project'],
    tags: ['hierarchy']
  },
  {
    term: 'Project',
    slug: 'project',
    definition:
      'An individual renewable energy installation managed in Ilios. Projects are the lowest level of the organizational hierarchy and contain detailed operational, financial, and document data.',
    relatedTerms: ['Site', 'Asset', 'Company'],
    tags: ['hierarchy']
  },
  {
    term: 'Rollup',
    slug: 'rollup',
    definition:
      'The process of aggregating data from individual projects up through companies to the portfolio level. Different metrics use different aggregation methods (sum, weighted average, etc.).',
    relatedTerms: ['Portfolio', 'Aggregation'],
    tags: ['data', 'metrics']
  },
  {
    term: 'Role',
    slug: 'role',
    definition:
      'A named set of permissions assigned to a user that defines what modules they can access and what actions they can perform (view, edit) within each module.',
    relatedTerms: ['Permission', 'Access'],
    tags: ['admin', 'security']
  },
  {
    term: 'Site',
    slug: 'site',
    definition:
      'Another term for a project, typically referring to the physical location of a renewable energy installation. Used interchangeably with "project" and "asset" in Ilios.',
    relatedTerms: ['Project', 'Asset'],
    tags: ['general']
  },
  {
    term: 'SPV (Special Purpose Vehicle)',
    slug: 'spv',
    definition:
      'A legal entity created specifically to own and manage one or more renewable energy projects. SPVs appear as companies in the Ilios hierarchy.',
    relatedTerms: ['Company', 'Project'],
    tags: ['legal', 'hierarchy']
  },
  {
    term: 'Telemetry',
    slug: 'telemetry',
    definition:
      'Real-time data collected from monitoring equipment at project sites, including energy production, device status, weather conditions, and performance metrics.',
    relatedTerms: ['Inverter', 'Generation'],
    tags: ['o&m', 'data']
  },
  {
    term: 'Variance',
    slug: 'variance',
    definition:
      'The difference between budgeted and actual financial figures (Actual - Budget). Positive revenue variance is favorable; positive cost variance is unfavorable.',
    relatedTerms: ['Budget', 'Actuals'],
    tags: ['finance']
  },
  {
    term: 'Work Order',
    slug: 'work-order',
    definition:
      'A formal request for maintenance, repair, or inspection work at a project site. Work orders are created in the O&M module and track the full lifecycle of maintenance activities.',
    relatedTerms: ['Maintenance', 'O&M'],
    tags: ['o&m']
  }
];

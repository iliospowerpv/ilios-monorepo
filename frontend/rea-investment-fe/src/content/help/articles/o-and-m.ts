import { HelpArticle } from '../types';

export const oAndMArticles: HelpArticle[] = [
  {
    slug: 'o-and-m-overview',
    title: 'O&M Module Overview',
    summary:
      'Monitor operations and maintenance for your renewable energy projects including device performance, alerts, and work orders.',
    category: 'o-and-m',
    module: 'o-and-m',
    audience: ['all-users', 'operations'],
    articleType: 'overview',
    tags: ['o-and-m', 'operations', 'maintenance', 'monitoring', 'performance'],
    searchKeywords: [
      'o&m',
      'operations',
      'maintenance',
      'monitoring',
      'devices',
      'alerts',
      'performance',
      'availability'
    ],
    relatedArticles: ['o-and-m-workflows', 'o-and-m-performance-explained', 'o-and-m-key-screens'],
    lastUpdated: '2026-04-01',
    body: `## What Is the O&M Module?

The **Operations & Maintenance (O&M)** module provides real-time monitoring and management tools for operational renewable energy projects. It tracks device performance, generates alerts, and manages maintenance workflows.

## Key Features

### Performance Monitoring
- **Availability** — Track uptime and downtime for each device and site
- **Performance Ratio (PR)** — Measure actual vs expected energy production
- **Generation data** — Monitor energy output in real-time and historically

### Device Management
- View all devices (inverters, meters, weather stations) at a site
- Monitor individual device status and telemetry
- Track device-level performance metrics

### Alerts and Notifications
- Automated alerts for performance deviations
- Device communication failures
- Weather-related warnings
- Customizable alert thresholds

### Work Orders
- Create and track maintenance work orders
- Assign tasks to field teams
- Document repairs and inspections
- Track resolution times and costs

### Company and Portfolio Views
- **Portfolio view** — Aggregate O&M metrics across all sites
- **Company view** — O&M summary for sites under one company
- **Site view** — Detailed monitoring for individual projects

## Who Uses It

- **O&M Managers** — Daily monitoring and maintenance oversight
- **Field Technicians** — Work order management and reporting
- **Asset Managers** — Performance reviews and trend analysis
- **Executives** — Portfolio-wide performance dashboards

## Important Terms

- **Availability** — The percentage of time a device or site is operational
- **Performance Ratio (PR)** — Ratio of actual to theoretical energy output
- **Inverter** — Device that converts DC power from panels to AC power
- **Work Order** — A formal request for maintenance or repair work
- **Telemetry** — Real-time data from monitoring equipment`
  },
  {
    slug: 'o-and-m-workflows',
    title: 'O&M Common Workflows',
    summary: 'Day-to-day workflows for monitoring sites, responding to alerts, and managing maintenance activities.',
    category: 'o-and-m',
    module: 'o-and-m',
    audience: ['operations'],
    articleType: 'tutorial',
    tags: ['o-and-m', 'workflow', 'monitoring', 'maintenance'],
    searchKeywords: ['monitor site', 'check performance', 'respond alert', 'create work order', 'daily monitoring'],
    relatedArticles: ['o-and-m-overview', 'o-and-m-key-screens', 'o-and-m-performance-explained'],
    lastUpdated: '2026-04-01',
    body: `## Daily Site Monitoring

1. Navigate to the **O&M** module from the sidebar
2. Review the portfolio-level dashboard for any red flags
3. Check the alerts panel for new or unresolved alerts
4. Drill into any site showing anomalous performance
5. Review device-level data for affected sites

## Responding to Alerts

1. Open the alerts section from the O&M module
2. Review the alert details (type, severity, affected device)
3. Assess whether the issue requires a site visit
4. Create a work order if maintenance is needed
5. Acknowledge the alert to indicate it's being addressed

## Creating a Work Order

1. From the O&M site view, click **Create Work Order**
2. Select the work order type (corrective, preventive, inspection)
3. Describe the issue or planned maintenance
4. Assign to a technician or team
5. Set priority and expected completion date
6. Submit the work order

## Reviewing Site Performance

1. Navigate to a specific site in O&M
2. Review the performance dashboard:
   - Daily/weekly/monthly generation
   - Availability trends
   - Performance ratio history
3. Compare actual performance against expectations
4. Identify any degradation trends

## Completing a Work Order

1. Open the assigned work order
2. Document the work performed
3. Attach photos or reports if applicable
4. Update device status if changes were made
5. Mark the work order as complete`
  },
  {
    slug: 'o-and-m-key-screens',
    title: 'O&M Key Screens',
    summary: 'Tour of the main O&M module screens and their features.',
    category: 'o-and-m',
    module: 'o-and-m',
    audience: ['operations'],
    articleType: 'guide',
    tags: ['o-and-m', 'screens', 'interface'],
    searchKeywords: ['o&m screen', 'monitoring dashboard', 'device view', 'alert panel', 'work order list'],
    relatedArticles: ['o-and-m-overview', 'o-and-m-workflows'],
    lastUpdated: '2026-04-01',
    body: `## Portfolio O&M Dashboard

The top-level O&M view shows:
- **Company list** — All companies with aggregate O&M metrics
- **Performance summary** — Portfolio-wide availability and generation
- **Alert summary** — Count of active alerts by severity

## Company O&M View

Drilling into a company shows:
- **Overview tab** — Company-level O&M metrics
- **Sites tab** — All sites with individual performance metrics
- **Alerts tab** — Company-level alert feed
- **Tasks tab** — Company-level work orders and maintenance tasks

## Site O&M Detail

The site-level O&M view provides:
- **Performance dashboard** — Real-time and historical metrics
- **Device list** — All monitoring devices with status
- **Telemetry charts** — Time-series data visualization
- **Alert history** — All alerts for this site

## Alert Management

The alert interface shows:
- Alert type and severity (critical, warning, info)
- Affected device and site
- Timestamp and duration
- Status (new, acknowledged, resolved)
- Actions (acknowledge, create work order, dismiss)

## Telemetry View

Detailed time-series data visualization:
- Select devices and metrics to display
- Choose time range and granularity
- Compare multiple metrics on the same chart
- Export data for external analysis`
  },
  {
    slug: 'o-and-m-troubleshooting',
    title: 'O&M Troubleshooting',
    summary: 'Common O&M module issues and their solutions.',
    category: 'o-and-m',
    module: 'o-and-m',
    audience: ['operations'],
    articleType: 'troubleshooting',
    tags: ['o-and-m', 'troubleshooting'],
    searchKeywords: ['o&m problem', 'no data', 'telemetry missing', 'alerts not showing', 'device offline'],
    relatedArticles: ['o-and-m-overview', 'troubleshooting-stale-metrics', 'troubleshooting-empty-dashboards'],
    lastUpdated: '2026-04-01',
    body: `## No Telemetry Data Showing

**Possible causes:**
- The monitoring equipment may be offline
- Data feeds may be delayed
- The project may not have reached operational status

**Solution:** Check if the project is in an operational lifecycle stage. Verify that monitoring equipment is connected. Telemetry data may have a 15-60 minute delay depending on the data source.

## Performance Metrics Look Incorrect

**Possible causes:**
- Irradiance data may be missing or incorrect
- Device capacity configurations may be wrong
- Calculation periods may not match expectations

**Solution:** Verify the site's configuration data (capacity, expected generation). Check that weather station data is being received. Contact support if metrics appear systematically wrong.

## Alerts Not Appearing

**Possible causes:**
- Alert thresholds may not be configured for this site
- You may not have O&M view permissions
- The site may not have active monitoring

**Solution:** Verify that alert rules are configured for the site. Check your permissions include O&M access. Ensure the site has active telemetry feeds.

## Work Orders Not Saving

**Cause:** You may not have edit permissions for O&M tasks.

**Solution:** Verify your role includes O&M edit permissions. Contact your administrator if access needs to be adjusted.`
  }
];

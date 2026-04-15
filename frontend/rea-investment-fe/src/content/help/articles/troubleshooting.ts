import { HelpArticle } from '../types';

export const troubleshootingArticles: HelpArticle[] = [
  {
    slug: 'troubleshooting-missing-data',
    title: 'Troubleshooting: Missing Data',
    summary: 'What to do when expected data is not showing in Ilios dashboards or reports.',
    category: 'troubleshooting',
    audience: ['all-users'],
    articleType: 'troubleshooting',
    tags: ['troubleshooting', 'missing-data', 'no-data', 'empty'],
    searchKeywords: ['missing data', 'no data', 'data not showing', 'empty', 'blank', 'where is my data'],
    relatedArticles: [
      'troubleshooting-empty-dashboards',
      'troubleshooting-permissions',
      'troubleshooting-stale-metrics'
    ],
    lastUpdated: '2026-04-01',
    body: `## Common Causes of Missing Data

### 1. Permission Restrictions
Your role may not include access to the data you're looking for.

**How to check:** Try switching to a different module that you know you have access to. If that works, the issue is likely permission-based.

**Solution:** Contact your administrator to review your role permissions.

### 2. Scope Mismatch
You may be viewing data at the wrong hierarchical level.

**How to check:** Look at the breadcrumbs and scope selector to confirm you're viewing the right portfolio, company, or project.

**Solution:** Adjust the scope selector or navigate to the correct entity.

### 3. Date Range Issues
The selected date range may not include the period you're looking for.

**How to check:** Review the date range or period selector on the current view.

**Solution:** Adjust the date range to include the desired period.

### 4. Data Not Yet Entered
The data may simply not have been entered into the system yet.

**How to check:** Check with the team responsible for entering the data (e.g., finance team for actuals).

**Solution:** Enter the missing data or wait for the responsible team to do so.

### 5. Data Source Delays
Some data (like telemetry) may have inherent delays.

**How to check:** Note when the data was last updated (usually shown in metadata or timestamps).

**Solution:** Wait for the data feed to update. Telemetry data may have 15-60 minute delays.

## Quick Checklist

1. ✅ Check your permissions
2. ✅ Verify the scope (portfolio/company/project)
3. ✅ Check the date range
4. ✅ Confirm data has been entered
5. ✅ Look for data source update timestamps
6. ✅ Try refreshing the page
7. ✅ Clear browser cache if issue persists`
  },
  {
    slug: 'troubleshooting-permissions',
    title: 'Troubleshooting: Permission Issues',
    summary: 'Resolving access and permission problems in Ilios.',
    category: 'troubleshooting',
    audience: ['all-users'],
    articleType: 'troubleshooting',
    tags: ['troubleshooting', 'permissions', 'access', 'locked'],
    searchKeywords: [
      'permission denied',
      'access denied',
      'cannot access',
      'locked out',
      'no permission',
      'grayed out'
    ],
    relatedArticles: ['permissions-and-access', 'troubleshooting-missing-data', 'portfolio-admin-overview'],
    lastUpdated: '2026-04-01',
    body: `## "You Don't Have Permission" Message

**What it means:** Your role doesn't include the necessary permission for the module or action.

**What to do:**
1. Note which module or action triggered the message
2. Contact your portfolio administrator
3. Provide the specific module name and what you were trying to do
4. The administrator can adjust your role or assign a different role

## Module Grayed Out in Sidebar

**What it means:** Your role doesn't include view permission for that module.

**What to do:**
1. Check with your administrator about your role assignment
2. If you need access, request a role change that includes the needed module

## Can See But Can't Edit

**What it means:** Your role has view permission but not edit permission for the module.

**What to do:**
1. If you need edit access, request a role update from your administrator
2. Note which specific actions you need to perform

## Permissions Changed But No Effect

**What to do:**
1. Log out and log back in — permissions are loaded at login
2. Clear your browser cache
3. If the issue persists, ask the administrator to verify the role configuration

## Cannot See Specific Projects or Companies

**What it means:** Your access scope may be limited to certain entities.

**What to do:**
1. Contact your administrator to check your entity access scope
2. You may only be assigned to view certain companies or projects`
  },
  {
    slug: 'troubleshooting-empty-dashboards',
    title: 'Troubleshooting: Empty Dashboards',
    summary: 'Why dashboard pages might appear empty and how to resolve it.',
    category: 'troubleshooting',
    audience: ['all-users'],
    articleType: 'troubleshooting',
    tags: ['troubleshooting', 'dashboards', 'empty', 'no-content'],
    searchKeywords: [
      'empty dashboard',
      'blank page',
      'nothing showing',
      'dashboard empty',
      'no content',
      'blank dashboard'
    ],
    relatedArticles: ['troubleshooting-missing-data', 'troubleshooting-permissions', 'home-overview'],
    lastUpdated: '2026-04-01',
    body: `## Why Is My Dashboard Empty?

### No Projects Exist Yet
If your portfolio has no projects, dashboards won't have data to display.

**Solution:** Check with your administrator about onboarding projects into the system.

### New Account or Role
If you've just been added to Ilios, your dashboards may be empty until:
- Projects are assigned to your access scope
- Data exists for the periods you're viewing

### Wrong Scope Selected
You may be viewing an empty company or project that has no data.

**Solution:** Switch to portfolio-level view or select a different entity.

### Lifecycle Stage Mismatch
Some dashboard widgets only show data for projects in certain lifecycle stages (e.g., O&M data only for operational projects).

**Solution:** Verify the projects in your scope include ones in the relevant lifecycle stages.

### Browser or Cache Issues
Occasionally, cached data may cause display issues.

**Solution:**
1. Refresh the page (Ctrl+R or Cmd+R)
2. Try a hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
3. Clear browser cache if needed
4. Try a different browser`
  },
  {
    slug: 'troubleshooting-report-mismatches',
    title: 'Troubleshooting: Report Data Mismatches',
    summary: 'Why report numbers might differ from other module views and how to interpret the differences.',
    category: 'troubleshooting',
    audience: ['all-users'],
    articleType: 'troubleshooting',
    tags: ['troubleshooting', 'reports', 'mismatches', 'data-quality'],
    searchKeywords: ['report mismatch', 'numbers different', 'data inconsistency', 'report wrong', "doesn't match"],
    relatedArticles: ['reports-overview', 'portfolio-rollups-explained', 'troubleshooting-missing-data'],
    lastUpdated: '2026-04-01',
    body: `## Why Do Report Numbers Differ From Module Views?

### Different Time Periods
Reports may calculate over different date ranges than what's shown in a module view.

**Solution:** Verify both the report and the module are using the same time period.

### Rollup Differences
Portfolio-level reports aggregate data differently than browsing individual projects.

**Explanation:** Reports use standardized rollup logic (see Portfolio Rollups Explained), while individual module views may show raw values.

### Data Refresh Timing
Reports may be based on a snapshot taken at a specific time, while module views show real-time data.

**Solution:** Check when the report was last refreshed. Some data sources update on different schedules.

### Scope Differences
Reports may include/exclude projects based on criteria that differ from your current navigation.

**Solution:** Verify the report's scope settings match the entities you're comparing against.

### Rounding and Precision
Reports may round numbers differently than detailed module views.

**Explanation:** Summary-level reports typically round to fewer decimal places for readability.

## How to Investigate

1. Note the exact figures that don't match
2. Check date ranges in both views
3. Verify the scope (portfolio/company/project) matches
4. Check for data refresh timestamps
5. If the discrepancy persists, contact your administrator`
  },
  {
    slug: 'troubleshooting-stale-metrics',
    title: 'Troubleshooting: Stale Metrics',
    summary: 'What to do when metrics appear outdated or not reflecting recent changes.',
    category: 'troubleshooting',
    audience: ['all-users', 'operations'],
    articleType: 'troubleshooting',
    tags: ['troubleshooting', 'stale', 'metrics', 'outdated', 'refresh'],
    searchKeywords: ['stale data', 'old data', 'not updating', 'outdated', 'refresh data', 'last updated'],
    relatedArticles: ['troubleshooting-missing-data', 'o-and-m-overview', 'troubleshooting-report-mismatches'],
    lastUpdated: '2026-04-01',
    body: `## Why Metrics May Appear Stale

### Telemetry Delays
O&M metrics depend on telemetry data from monitoring equipment. This data may be delayed by:
- 15-60 minutes for standard monitoring
- Several hours if a data source is experiencing issues
- Days if monitoring equipment is offline

### Calculation Schedules
Some aggregate metrics are calculated on schedules rather than in real-time:
- Daily performance calculations
- Weekly or monthly rollup updates
- Financial data typically updated monthly

### Data Entry Lag
Financial and manual data depends on human input:
- Budget data needs to be entered before periods
- Actuals are typically entered monthly
- Task status requires manual updates

## How to Check Data Freshness

1. Look for "Last Updated" timestamps on dashboards and reports
2. Check the data source status in O&M for telemetry feeds
3. Review the time range — are you looking at a period that hasn't been updated yet?

## What to Do

### For Telemetry Data
- Check if the monitoring equipment is online in the O&M device view
- Wait for the data feed to catch up (usually within an hour)
- If data is consistently delayed, report the monitoring issue

### For Financial Data
- Verify that the finance team has entered data for the current period
- Check the financial readiness score for data completeness

### For Calculated Metrics
- Refresh the page to trigger a recalculation
- Wait for the next scheduled calculation cycle
- Some metrics update overnight`
  },
  {
    slug: 'troubleshooting-uploads',
    title: 'Troubleshooting: Upload Issues',
    summary: 'Resolving problems with file uploads in the Data Room and other modules.',
    category: 'troubleshooting',
    audience: ['all-users'],
    articleType: 'troubleshooting',
    tags: ['troubleshooting', 'uploads', 'files', 'data-room'],
    searchKeywords: [
      'upload failed',
      'upload error',
      'file too large',
      'cannot upload',
      'upload problem',
      'file rejected'
    ],
    relatedArticles: ['data-room-overview', 'data-room-workflows', 'troubleshooting-permissions'],
    lastUpdated: '2026-04-01',
    body: `## Upload Fails Immediately

### File Too Large
**Symptom:** Error message about file size.
**Solution:** Reduce file size (compress images, split large PDFs) or check the maximum upload size for your account.

### Unsupported File Type
**Symptom:** Error about file format.
**Solution:** Convert the file to a supported format. Common supported types include PDF, DOCX, XLSX, CSV, JPG, PNG.

### Permission Issues
**Symptom:** Upload button is disabled or error about permissions.
**Solution:** Verify you have edit access to the Data Room or the relevant module.

## Upload Starts But Fails

### Network Issues
**Symptom:** Upload progress bar stops or errors out mid-upload.
**Solution:**
1. Check your internet connection
2. Try again on a stable connection
3. For large files, use a wired connection if possible

### Session Timeout
**Symptom:** Upload fails after a long time.
**Solution:** Very large uploads may exceed session timeouts. Try uploading smaller files or batches.

## Upload Succeeds But File Not Visible

### Wrong Category
**Solution:** Check all document categories — the file may have been uploaded to a different category than expected.

### Browser Cache
**Solution:** Refresh the page to see newly uploaded files.

### Processing Delay
Some file types require processing after upload (e.g., generating previews). Wait a few moments and refresh.

## Best Practices for Uploads

1. Use descriptive file names
2. Select the correct category before uploading
3. Upload one batch at a time to avoid errors
4. Verify uploads by checking the file list after completion`
  }
];

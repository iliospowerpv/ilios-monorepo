import { FAQItem } from './types';

export const faqItems: FAQItem[] = [
  {
    id: 'faq-what-is-ilios',
    question: 'What is Ilios?',
    answer:
      'Ilios is a comprehensive renewable energy investment management platform. It provides tools for tracking acquisitions, managing projects, monitoring operations, tracking finances, and generating reports across your renewable energy portfolio.',
    group: 'General',
    tags: ['general', 'overview']
  },
  {
    id: 'faq-who-is-ilios-for',
    question: 'Who is Ilios designed for?',
    answer:
      'Ilios is designed for renewable energy investment firms, asset managers, operations teams, and financial analysts who manage portfolios of solar, wind, and energy storage projects.',
    group: 'General',
    tags: ['general', 'users']
  },
  {
    id: 'faq-supported-technologies',
    question: 'What types of renewable energy does Ilios support?',
    answer:
      'Ilios supports solar PV, wind, and energy storage projects. The platform is designed to accommodate the unique monitoring, financial, and operational needs of each technology type.',
    group: 'General',
    tags: ['general', 'technology']
  },
  {
    id: 'faq-get-started',
    question: 'How do I get started with Ilios?',
    answer:
      'After receiving your login credentials, sign in and explore the Home page for an overview of your portfolio. Start by navigating the sidebar to familiarize yourself with each module. Check the Getting Started articles in this help center for detailed guides.',
    group: 'General',
    tags: ['general', 'onboarding']
  },

  {
    id: 'faq-navigate-modules',
    question: 'How do I navigate between modules?',
    answer:
      'Use the sidebar on the left side of the screen. Each icon represents a module. Click the icon or label to navigate. The sidebar can be collapsed to show only icons for more screen space.',
    group: 'Navigation',
    tags: ['navigation', 'sidebar']
  },
  {
    id: 'faq-breadcrumbs',
    question: 'What are breadcrumbs and how do I use them?',
    answer:
      'Breadcrumbs appear at the top of most pages showing your current location in the hierarchy (e.g., Portfolio > Company > Project). Click any level to navigate back up. They help you maintain orientation as you drill into detailed views.',
    group: 'Navigation',
    tags: ['navigation', 'breadcrumbs']
  },
  {
    id: 'faq-scope-selector',
    question: 'What is the scope selector?',
    answer:
      'The scope selector lets you switch between portfolio-level, company-level, and project-level views within a module. This allows you to see aggregated data or drill into specific entities without navigating away from your current module.',
    group: 'Navigation',
    tags: ['navigation', 'scope']
  },
  {
    id: 'faq-project-picker',
    question: 'Why does a project picker appear when I click a module?',
    answer:
      "Some modules (Data Room, O&M, Tasks) require a specific project context. If you haven't selected a project yet, the picker will appear so you can choose which project to view. Modules like Finance and Reports work at the portfolio level and don't require this.",
    group: 'Navigation',
    tags: ['navigation', 'project-picker']
  },

  {
    id: 'faq-deal-vs-project',
    question: 'What is the difference between a deal and a project?',
    answer:
      'A deal is a potential investment opportunity tracked in the Acquisitions module. A project is an active, confirmed investment managed in the Project Hub. Deals can be converted to projects once acquisition is complete. See the "Projects vs Deals" article for details.',
    group: 'Deals & Projects',
    tags: ['deals', 'projects']
  },
  {
    id: 'faq-convert-deal',
    question: 'How do I convert a deal to a project?',
    answer:
      'Deal-to-project conversion is initiated from the Acquisitions module once the deal has progressed through all pipeline stages and the acquisition closes. An administrator or acquisitions lead performs the conversion, which creates a new project record in the Project Hub.',
    group: 'Deals & Projects',
    tags: ['deals', 'projects', 'conversion']
  },
  {
    id: 'faq-project-lifecycle',
    question: 'What are project lifecycle stages?',
    answer:
      'Lifecycle stages track where a project is in its journey: Development, Pre-Construction, Construction, Commissioning, NTP, COD, Operations, and Decommissioning. The stage affects which modules are active and what data is relevant.',
    group: 'Deals & Projects',
    tags: ['projects', 'lifecycle']
  },
  {
    id: 'faq-add-project',
    question: 'How do I add a new project?',
    answer:
      'Projects can be created through deal conversion in Acquisitions, or directly added by an administrator through Portfolio Admin. Direct creation is typically used for projects acquired outside the Ilios platform.',
    group: 'Deals & Projects',
    tags: ['projects', 'create']
  },

  {
    id: 'faq-who-sees-what',
    question: 'Can other users see my data?',
    answer:
      'Data visibility is controlled by role permissions and access scope. Users can only see modules their role permits and entities (companies/projects) within their assigned scope. Administrators configure these settings in Portfolio Admin.',
    group: 'Data Visibility',
    tags: ['permissions', 'visibility', 'data']
  },
  {
    id: 'faq-data-export',
    question: 'Can I export data from Ilios?',
    answer:
      'Yes, many modules support data export. Look for export buttons or download options in report views, data tables, and dashboard sections. Export formats vary by module.',
    group: 'Data Visibility',
    tags: ['export', 'data', 'download']
  },
  {
    id: 'faq-data-refresh',
    question: 'How often is data refreshed?',
    answer:
      'Telemetry data refreshes every 15-60 minutes depending on the data source. Financial data is typically updated monthly. Dashboard rollup calculations may run daily or on-demand. Check "Last Updated" timestamps for specific data points.',
    group: 'Data Visibility',
    tags: ['data', 'refresh', 'timing']
  },

  {
    id: 'faq-om-availability',
    question: 'What does availability mean in O&M?',
    answer:
      'Availability is the percentage of time that equipment is operational and capable of generating energy. It is calculated as (Total Hours - Downtime) / Total Hours × 100%. Most solar projects target 97-99% availability.',
    group: 'O&M',
    tags: ['o&m', 'availability', 'metrics']
  },
  {
    id: 'faq-om-pr',
    question: 'What is performance ratio (PR)?',
    answer:
      'Performance ratio measures how effectively a solar installation converts available sunlight into electricity. It accounts for all system losses including temperature, shading, soiling, and equipment efficiency. Typical PR ranges from 75-85%.',
    group: 'O&M',
    tags: ['o&m', 'performance-ratio', 'metrics']
  },
  {
    id: 'faq-om-alerts',
    question: 'How do O&M alerts work?',
    answer:
      'Alerts are generated automatically when monitoring data indicates an issue — device communication failures, performance deviations, or threshold breaches. Alerts are categorized by severity (Critical, Warning, Info) and appear in the O&M module for review and response.',
    group: 'O&M',
    tags: ['o&m', 'alerts', 'monitoring']
  },

  {
    id: 'faq-finance-readiness',
    question: 'What is financial readiness?',
    answer:
      "Financial readiness is a scoring system that evaluates how complete and reliable a project's financial data is. It considers budget completeness, actuals timeliness, and data quality. A high readiness score means the financial data is trustworthy for reporting.",
    group: 'Finance',
    tags: ['finance', 'readiness', 'scoring']
  },
  {
    id: 'faq-budget-vs-actual',
    question: 'How does budget vs actual work?',
    answer:
      'The Finance module compares planned budget figures against actual recorded figures for each financial line item. The variance (difference) is calculated and displayed. Positive revenue variance is favorable; positive cost variance is unfavorable.',
    group: 'Finance',
    tags: ['finance', 'budget', 'actuals', 'variance']
  },
  {
    id: 'faq-finance-periods',
    question: 'What time periods does Finance support?',
    answer:
      'Finance supports monthly, quarterly, and annual periods. You can view budget vs actual comparisons for any of these periods, as well as year-to-date summaries.',
    group: 'Finance',
    tags: ['finance', 'periods', 'time']
  },

  {
    id: 'faq-report-types',
    question: 'What types of reports are available?',
    answer:
      'Ilios provides performance reports (generation, availability, PR), financial reports (revenue, costs, budget variance), operational reports (work orders, tasks), and portfolio reports (cross-project analytics). Reports can be scoped to portfolio, company, or project level.',
    group: 'Reports',
    tags: ['reports', 'types']
  },
  {
    id: 'faq-report-scope',
    question: 'How do I change the scope of a report?',
    answer:
      'Use the scope selector in the header area when viewing reports. You can switch between portfolio-wide, company-level, and project-level views. The report data will refresh to show information for the selected scope.',
    group: 'Reports',
    tags: ['reports', 'scope']
  },

  {
    id: 'faq-admin-add-user',
    question: 'How do I add a new user?',
    answer:
      'Navigate to Portfolio Admin, go to user management, and click "Add User" or "Invite User." Enter the user\'s email, assign a role, and set their access scope. The user will receive an email invitation to join.',
    group: 'Admin',
    tags: ['admin', 'users', 'invite']
  },
  {
    id: 'faq-admin-change-role',
    question: "How do I change a user's role?",
    answer:
      'In Portfolio Admin, find the user in the user management section. Edit their profile and select a different role. Changes take effect after the user logs out and back in.',
    group: 'Admin',
    tags: ['admin', 'roles', 'users']
  },
  {
    id: 'faq-admin-create-role',
    question: 'Can I create custom roles?',
    answer:
      "Yes, administrators can create custom roles in Portfolio Admin. Each role defines view and edit permissions for every module. This allows you to create roles that match your organization's specific access requirements.",
    group: 'Admin',
    tags: ['admin', 'roles', 'custom']
  },

  {
    id: 'faq-home-customize',
    question: 'Can I customize the Home page dashboard?',
    answer:
      'The Home page automatically adapts to your role and permissions. While you cannot rearrange widgets, the content shown is personalized to display metrics, activity, and alerts relevant to the projects and modules you have access to.',
    group: 'Home',
    tags: ['home', 'dashboard', 'customize']
  },
  {
    id: 'faq-home-activity',
    question: 'What shows up in the Home activity feed?',
    answer:
      'The activity feed shows recent changes across projects you have access to, including document uploads, task completions, status changes, and financial updates. Items are displayed chronologically with links to the affected record.',
    group: 'Home',
    tags: ['home', 'activity', 'feed']
  },

  {
    id: 'faq-project-hub-navigate',
    question: 'How do I navigate the Project Hub?',
    answer:
      'The Project Hub uses a hierarchy of Portfolio > Company > Project. Start at the top level to see all companies, click a company to see its projects, and click a project to access its details including Data Room, O&M, Finance, and Tasks tabs.',
    group: 'Project Hub',
    tags: ['project-hub', 'navigation', 'hierarchy']
  },
  {
    id: 'faq-project-hub-tabs',
    question: 'What tabs are available on a project page?',
    answer:
      'Each project page includes tabs for Overview, Data Room, O&M, Finance, and Tasks. The available tabs depend on the project lifecycle stage and your role permissions. Some tabs may be hidden if the module is not relevant to the project stage.',
    group: 'Project Hub',
    tags: ['project-hub', 'tabs', 'modules']
  },

  {
    id: 'faq-data-room-upload',
    question: 'How do I upload documents to the Data Room?',
    answer:
      'Navigate to the Data Room tab within a project, select the appropriate section or category, and use the upload button to add files. You can upload multiple files at once. Documents are organized by section and can be tagged for easy retrieval.',
    group: 'Data Room',
    tags: ['data-room', 'upload', 'documents']
  },
  {
    id: 'faq-data-room-diligence',
    question: 'What is the due diligence workflow in the Data Room?',
    answer:
      'Due diligence workflows track the review status of required documents for a project. Each diligence item has a status (Not Started, In Progress, Complete) and can be assigned to a reviewer. The workflow provides a checklist view of all required documentation.',
    group: 'Data Room',
    tags: ['data-room', 'diligence', 'workflow']
  },

  {
    id: 'faq-tasks-assign',
    question: 'How do I assign a task to someone?',
    answer:
      'Open the Tasks module for a project, click "Create Task" or edit an existing task, and use the assignee field to select a team member. The assignee will see the task in their task list and on their Home page activity feed.',
    group: 'Tasks',
    tags: ['tasks', 'assign', 'create']
  },
  {
    id: 'faq-tasks-status',
    question: 'What task statuses are available?',
    answer:
      'Tasks use statuses like Open, In Progress, Review, and Complete. Status transitions may follow defined workflows depending on your project configuration. Updating status is done from the task detail view or inline in the task list.',
    group: 'Tasks',
    tags: ['tasks', 'status', 'workflow']
  },

  {
    id: 'faq-trouble-login',
    question: "I can't log in to Ilios. What should I do?",
    answer:
      'First, verify you\'re using the correct email address. Try the "Forgot Password" link to reset your password. If you still can\'t log in, contact your administrator to verify your account is active and properly configured.',
    group: 'Troubleshooting',
    tags: ['troubleshooting', 'login', 'access']
  },
  {
    id: 'faq-trouble-slow',
    question: 'Why is Ilios loading slowly?',
    answer:
      'Slow loading can be caused by network connectivity issues, large data sets being loaded, or browser cache problems. Try refreshing the page, clearing browser cache, or checking your internet connection. If the issue persists, try a different browser.',
    group: 'Troubleshooting',
    tags: ['troubleshooting', 'performance', 'slow']
  },
  {
    id: 'faq-trouble-module-disabled',
    question: 'Why is a module grayed out in the sidebar?',
    answer:
      "A grayed-out module means your role doesn't include access permission for it, or the module requires a project selection. Contact your administrator if you need access, or click the module to trigger the project picker if applicable.",
    group: 'Troubleshooting',
    tags: ['troubleshooting', 'permissions', 'modules']
  },
  {
    id: 'faq-trouble-data-mismatch',
    question: 'Why do numbers in reports differ from module views?',
    answer:
      'Differences may be due to different time periods, rollup calculation methods, data refresh timing, or scope differences. Check that both views use the same date range and scope. See the "Report Data Mismatches" troubleshooting article for details.',
    group: 'Troubleshooting',
    tags: ['troubleshooting', 'reports', 'data']
  }
];

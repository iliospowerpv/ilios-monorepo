export type ArticleType = 'guide' | 'overview' | 'reference' | 'tutorial' | 'concept' | 'troubleshooting' | 'faq';

export type AudienceTag =
  | 'all-users'
  | 'admin'
  | 'finance'
  | 'operations'
  | 'acquisitions'
  | 'asset-manager'
  | 'executive';

export type HelpCategory =
  | 'getting-started'
  | 'home'
  | 'acquisitions'
  | 'project-hub'
  | 'data-room'
  | 'o-and-m'
  | 'finance'
  | 'tasks'
  | 'reports'
  | 'portfolio-admin'
  | 'concepts'
  | 'reference'
  | 'troubleshooting'
  | 'faq'
  | 'glossary';

export type HelpModule =
  | 'home'
  | 'acquisitions'
  | 'project-hub'
  | 'data-room'
  | 'o-and-m'
  | 'finance'
  | 'tasks'
  | 'reports'
  | 'portfolio-admin';

export interface HelpArticle {
  slug: string;
  title: string;
  summary: string;
  category: HelpCategory;
  module?: HelpModule;
  audience: AudienceTag[];
  articleType: ArticleType;
  tags: string[];
  searchKeywords: string[];
  relatedArticles: string[];
  lastUpdated: string;
  body: string;
}

export interface FAQItem {
  id: string;
  question: string;
  answer: string;
  group: string;
  tags: string[];
}

export interface GlossaryEntry {
  term: string;
  slug: string;
  definition: string;
  relatedTerms: string[];
  tags: string[];
}

export interface HelpCategoryMeta {
  id: HelpCategory;
  title: string;
  description: string;
  icon: string;
  order: number;
}

export const categoryMeta: HelpCategoryMeta[] = [
  {
    id: 'getting-started',
    title: 'Getting Started',
    description: 'Learn the basics of Ilios and get up and running quickly.',
    icon: 'RocketLaunch',
    order: 0
  },
  {
    id: 'home',
    title: 'Home',
    description: 'Your personalized dashboard and workspace overview.',
    icon: 'Home',
    order: 1
  },
  {
    id: 'acquisitions',
    title: 'Acquisitions',
    description: 'Track and manage deals through the acquisition pipeline.',
    icon: 'TrendingUp',
    order: 2
  },
  {
    id: 'project-hub',
    title: 'Project Hub',
    description: 'Central hub for managing projects and company portfolios.',
    icon: 'AccountBalance',
    order: 3
  },
  {
    id: 'data-room',
    title: 'Data Room',
    description: 'Secure document management and due diligence workflows.',
    icon: 'Folder',
    order: 4
  },
  {
    id: 'o-and-m',
    title: 'O&M',
    description: 'Operations and maintenance monitoring for active projects.',
    icon: 'Whatshot',
    order: 5
  },
  {
    id: 'finance',
    title: 'Finance',
    description: 'Financial tracking, budgets, actuals, and readiness scoring.',
    icon: 'AccountBalanceWallet',
    order: 6
  },
  {
    id: 'tasks',
    title: 'Tasks',
    description: 'Task management and workflow tracking across projects.',
    icon: 'AssignmentTurnedIn',
    order: 7
  },
  {
    id: 'reports',
    title: 'Reports',
    description: 'Generate and view reports across your portfolio.',
    icon: 'Assessment',
    order: 8
  },
  {
    id: 'portfolio-admin',
    title: 'Portfolio Admin',
    description: 'Administration settings for portfolios, companies, and projects.',
    icon: 'AdminPanelSettings',
    order: 9
  },
  {
    id: 'concepts',
    title: 'Concepts',
    description: 'Deep dives into how key Ilios features and workflows operate.',
    icon: 'Lightbulb',
    order: 10
  },
  {
    id: 'reference',
    title: 'Reference',
    description: 'Field definitions, KPIs, status codes, and technical details.',
    icon: 'MenuBook',
    order: 11
  },
  {
    id: 'troubleshooting',
    title: 'Troubleshooting',
    description: 'Solutions for common issues and error resolution.',
    icon: 'Build',
    order: 12
  },
  {
    id: 'faq',
    title: 'FAQs',
    description: 'Frequently asked questions about the Ilios platform.',
    icon: 'QuestionAnswer',
    order: 13
  },
  {
    id: 'glossary',
    title: 'Glossary',
    description: 'Definitions of key terms used throughout Ilios.',
    icon: 'Abc',
    order: 14
  }
];

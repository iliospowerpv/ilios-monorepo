import { HelpArticle } from '../types';

export const tasksArticles: HelpArticle[] = [
  {
    slug: 'tasks-overview',
    title: 'Tasks Module Overview',
    summary: 'Manage and track tasks across your projects with assignment, prioritization, and status tracking.',
    category: 'tasks',
    module: 'tasks',
    audience: ['all-users'],
    articleType: 'overview',
    tags: ['tasks', 'management', 'workflow', 'assignment'],
    searchKeywords: ['tasks', 'task management', 'assign', 'todo', 'work', 'action items', 'track'],
    relatedArticles: ['tasks-workflows', 'tasks-key-screens'],
    lastUpdated: '2026-04-01',
    body: `## What Is the Tasks Module?

The **Tasks** module provides task management capabilities across your projects. It allows teams to create, assign, track, and complete tasks related to project management, maintenance, and operations.

## Key Features

### Task Creation
Create tasks with:
- Title and description
- Priority level (low, medium, high, critical)
- Assignee
- Due date
- Associated project or company
- Category/type

### Task Tracking
- View tasks by status (open, in progress, completed, overdue)
- Filter by assignee, project, priority, or date
- Sort and search the task list

### Task Assignment
- Assign tasks to team members
- Reassign tasks as needed
- Track who is responsible for what

### Task Context
Tasks are associated with either:
- A specific **project** — accessible from the Project Hub's Tasks tab
- A specific **company** — for company-level administrative tasks

## Who Uses It

- **Project Managers** — Create and manage project tasks
- **O&M Teams** — Track maintenance and work order tasks
- **All team members** — View and complete assigned tasks

## Important Terms

- **Task** — A unit of work to be completed by an assignee
- **Priority** — The urgency level of a task
- **Status** — The current state of a task (open, in progress, done)
- **Assignee** — The person responsible for completing the task`
  },
  {
    slug: 'tasks-workflows',
    title: 'Tasks Workflows',
    summary: 'How to create, assign, and manage tasks effectively.',
    category: 'tasks',
    module: 'tasks',
    audience: ['all-users'],
    articleType: 'tutorial',
    tags: ['tasks', 'workflow', 'create', 'assign'],
    searchKeywords: ['create task', 'assign task', 'complete task', 'manage tasks', 'task workflow'],
    relatedArticles: ['tasks-overview', 'tasks-key-screens'],
    lastUpdated: '2026-04-01',
    body: `## Creating a New Task

1. Navigate to a project in the **Project Hub**
2. Select the **Tasks** tab
3. Click **Create Task** or **New Task**
4. Fill in the task details:
   - Title — Clear, descriptive name
   - Description — Detailed information about the work
   - Priority — Low, Medium, High, or Critical
   - Assignee — Who should complete the task
   - Due Date — When the task should be completed
5. Click **Save** to create the task

## Managing Your Tasks

1. Check the Tasks tab in your projects regularly
2. Update task status as you progress (Open → In Progress → Done)
3. Add comments or notes as work progresses
4. Mark tasks complete when finished

## Reviewing Team Tasks

1. Navigate to a project's Tasks tab
2. Filter by assignee to see individual workloads
3. Sort by due date to identify upcoming deadlines
4. Check for overdue tasks that need attention

## Task Prioritization

Use priority levels consistently:
- **Critical** — Must be done immediately, blocking other work
- **High** — Should be completed this week
- **Medium** — Important but not urgent
- **Low** — Nice to have, can be deferred`
  },
  {
    slug: 'tasks-key-screens',
    title: 'Tasks Key Screens',
    summary: 'Overview of the Tasks interface and its components.',
    category: 'tasks',
    module: 'tasks',
    audience: ['all-users'],
    articleType: 'guide',
    tags: ['tasks', 'screens', 'interface'],
    searchKeywords: ['task screen', 'task list', 'task detail', 'task view'],
    relatedArticles: ['tasks-overview', 'tasks-workflows'],
    lastUpdated: '2026-04-01',
    body: `## Task List View

The main tasks interface shows:
- **Task table** — Sortable list with title, assignee, priority, status, due date
- **Filters** — Filter by status, priority, assignee, date range
- **Actions** — Create new task, bulk operations

## Task Detail View

Clicking a task opens:
- **Task header** — Title, priority badge, status
- **Details** — Full description, metadata
- **Activity** — History of changes and comments
- **Actions** — Edit, reassign, change status, delete

## Company-Level Tasks

From a company view in Project Hub:
- **Tasks tab** — Shows all tasks across the company's projects
- **Aggregated view** — See task counts and status distribution
- **Cross-project management** — Manage tasks spanning multiple projects`
  },
  {
    slug: 'tasks-troubleshooting',
    title: 'Tasks Troubleshooting',
    summary: 'Common task management issues and solutions.',
    category: 'tasks',
    module: 'tasks',
    audience: ['all-users'],
    articleType: 'troubleshooting',
    tags: ['tasks', 'troubleshooting'],
    searchKeywords: ['task problem', 'cannot create task', 'task not showing', 'task stuck'],
    relatedArticles: ['tasks-overview', 'troubleshooting-permissions'],
    lastUpdated: '2026-04-01',
    body: `## Cannot Create Tasks

**Cause:** You may not have edit permissions for the Tasks or Project Hub module.

**Solution:** Contact your administrator to request edit access.

## Tasks Not Appearing

**Possible causes:**
- Filters may be hiding tasks
- You may be looking at the wrong project
- Tasks may have been completed or deleted

**Solution:** Clear all filters and verify you're viewing the correct project's task list.

## Cannot Change Task Status

**Cause:** You may only have view permissions, or the task may be assigned to someone else.

**Solution:** Verify your permissions. If the task is assigned to another user, you may need to be reassigned or have admin-level access.

## Overdue Tasks Not Highlighted

**Cause:** The due date may not be set on those tasks.

**Solution:** Ensure tasks have due dates assigned. Only tasks with due dates in the past will appear as overdue.`
  }
];

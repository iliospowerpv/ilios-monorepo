import { HelpArticle } from '../types';

export const portfolioAdminArticles: HelpArticle[] = [
  {
    slug: 'portfolio-admin-overview',
    title: 'Portfolio Admin Overview',
    summary: 'Manage portfolio, company, and project settings including user roles, permissions, and configuration.',
    category: 'portfolio-admin',
    module: 'portfolio-admin',
    audience: ['admin'],
    articleType: 'overview',
    tags: ['portfolio-admin', 'administration', 'settings', 'users', 'roles'],
    searchKeywords: [
      'admin',
      'settings',
      'users',
      'roles',
      'permissions',
      'configuration',
      'manage',
      'portfolio admin'
    ],
    relatedArticles: ['portfolio-admin-workflows', 'permissions-and-access', 'portfolio-admin-key-screens'],
    lastUpdated: '2026-04-01',
    body: `## What Is Portfolio Admin?

The **Portfolio Admin** module provides administrative tools for managing your organization's Ilios configuration. It uses the same three-level hierarchy (portfolio, company, project) for settings management.

## Key Features

### Portfolio-Level Administration
- Organization-wide settings
- User management and role assignment
- Global configuration options

### Company-Level Administration
- Company profile management
- Company-specific settings
- User access for company scope

### Project-Level Administration
- Project configuration and metadata
- Lifecycle stage management
- Project-specific settings

### User and Role Management
- Create and manage user accounts
- Define roles with module-level permissions
- Assign users to roles
- Manage access scope (which companies/projects a user can see)

## Who Uses It

- **Portfolio Administrators** — Primary users with full administrative access
- **Company Administrators** — Manage settings for their specific company
- **System Users** — Platform-wide administrative access

## Important Terms

- **Role** — A named set of permissions that can be assigned to users
- **Permission** — A specific capability (view, edit) for a module
- **Scope** — The companies and projects a user can access
- **System User** — A platform administrator with elevated access`
  },
  {
    slug: 'portfolio-admin-workflows',
    title: 'Portfolio Admin Workflows',
    summary: 'Common administrative workflows for managing users, roles, and settings.',
    category: 'portfolio-admin',
    module: 'portfolio-admin',
    audience: ['admin'],
    articleType: 'tutorial',
    tags: ['portfolio-admin', 'workflow', 'users', 'roles'],
    searchKeywords: ['add user', 'create role', 'manage permissions', 'admin workflow', 'change settings'],
    relatedArticles: ['portfolio-admin-overview', 'permissions-and-access', 'portfolio-admin-key-screens'],
    lastUpdated: '2026-04-01',
    body: `## Adding a New User

1. Navigate to **Portfolio Admin**
2. Go to user management
3. Click **Add User** or **Invite User**
4. Enter the user's email and name
5. Assign a role
6. Set the user's access scope (which companies/projects)
7. Save and send the invitation

## Creating or Modifying Roles

1. Open **Portfolio Admin** settings
2. Navigate to role management
3. Create a new role or edit an existing one
4. Configure permissions for each module:
   - Set view and/or edit access
5. Save the role changes

## Updating Project Settings

1. Navigate to **Portfolio Admin**
2. Select the project from the hierarchy
3. Update project metadata (name, capacity, location)
4. Change lifecycle stage if applicable
5. Save changes

## Managing Company Settings

1. Open **Portfolio Admin**
2. Select the company from the hierarchy
3. Update company profile information
4. Manage company-specific configurations
5. Save changes

## Reviewing Access Permissions

1. Go to **Portfolio Admin** user management
2. Select a user to view their role
3. Review the permissions assigned to their role
4. Adjust if needed and save`
  },
  {
    slug: 'portfolio-admin-key-screens',
    title: 'Portfolio Admin Key Screens',
    summary: 'Tour of the Portfolio Admin module interface.',
    category: 'portfolio-admin',
    module: 'portfolio-admin',
    audience: ['admin'],
    articleType: 'guide',
    tags: ['portfolio-admin', 'screens', 'interface'],
    searchKeywords: ['admin screen', 'user management', 'role management', 'settings page'],
    relatedArticles: ['portfolio-admin-overview', 'portfolio-admin-workflows'],
    lastUpdated: '2026-04-01',
    body: `## Portfolio Level

The top-level admin view shows:
- **Portfolio settings** — Organization-wide configuration
- **Company list** — All companies with management options
- **User overview** — Quick access to user management

## Company Level

Drilling into a company shows:
- **Company details** — Profile and metadata
- **Project list** — Projects under this company
- **Company settings** — Company-specific configuration

## Project Level

Project administration includes:
- **Project details** — Full metadata and configuration
- **Lifecycle management** — Stage transitions
- **Project settings** — Project-specific options

## User Management

The user management interface provides:
- **User list** — All users with role and status
- **Role assignment** — Change user roles
- **Access scope** — Configure entity access
- **Invitation management** — Send and manage invitations`
  },
  {
    slug: 'portfolio-admin-troubleshooting',
    title: 'Portfolio Admin Troubleshooting',
    summary: 'Common administrative issues and solutions.',
    category: 'portfolio-admin',
    module: 'portfolio-admin',
    audience: ['admin'],
    articleType: 'troubleshooting',
    tags: ['portfolio-admin', 'troubleshooting'],
    searchKeywords: ['admin problem', 'cannot add user', 'role not working', 'settings not saving'],
    relatedArticles: ['portfolio-admin-overview', 'troubleshooting-permissions'],
    lastUpdated: '2026-04-01',
    body: `## Cannot Access Portfolio Admin

**Cause:** Only users with administrator roles can access Portfolio Admin.

**Solution:** Verify with another administrator that your role includes Portfolio Admin access.

## User Permissions Not Taking Effect

**Possible causes:**
- The user may need to log out and back in
- The role may not be configured correctly
- Cached permissions may be stale

**Solution:** Ask the user to log out and log back in. Verify the role's permissions are correctly set for each module.

## Cannot Change a Project's Lifecycle Stage

**Cause:** Stage transitions may have requirements that aren't yet met, or you may not have the appropriate admin-level permissions.

**Solution:** Review the project's current state and ensure all prerequisites for the stage transition are met.

## User Invitation Not Received

**Possible causes:**
- Email may have gone to spam
- Email address may be incorrect

**Solution:** Verify the email address and ask the user to check their spam folder. Resend the invitation if needed.`
  },
  {
    slug: 'company-telemetry-administration',
    title: 'Company Telemetry Administration',
    summary:
      'License telemetry provider types, manage provider accounts and stored credentials, and review external sites at the company level.',
    category: 'portfolio-admin',
    module: 'portfolio-admin',
    audience: ['admin'],
    articleType: 'guide',
    tags: ['portfolio-admin', 'telemetry', 'integration', 'credentials', 'providers'],
    searchKeywords: [
      'telemetry',
      'provider',
      'credentials',
      'rotate',
      'sync sites',
      'AlsoEnergy',
      'KMC',
      'archived',
      'license',
      'verified',
      'unverified'
    ],
    relatedArticles: ['portfolio-admin-overview', 'portfolio-admin-workflows'],
    lastUpdated: '2026-04-27',
    body: `## What This Page Manages

The **Telemetry Administration** section on the Company page manages everything telemetry at the company scope:

- **Licensed Provider Types** — which telemetry vendors this company is allowed to use (for example AlsoEnergy or KMC)
- **Provider Accounts** — one per vendor login. Stores credentials write-only and tracks the lifecycle, credential, and sync status of each account
- **External Sites** — the inventory of sites synced from each provider

## Permissions

Mutations require the **Telemetry administrator** permission (or the legacy **Settings — edit** permission as a fallback). Users without those permissions see the tables in read-only mode; all action buttons are hidden.

## Three Status Indicators

Each Provider Account has three independent status chips:

- **Lifecycle** — Active, Paused, or Archived
- **Credentials** — Not tested, Verified, Invalid, or Expired
- **Sync** — Never synced, Synced, Partial, or Sync failed

## Adding a Licensed Provider Type

1. In **Licensed Provider Types**, click **Add Licensed Provider**
2. Pick a provider type from the catalog
3. Optionally add notes
4. Click **Add License**

Once licensed, you can create Provider Accounts that use this provider.

## Adding a Provider Account

1. In **Provider Accounts**, click **Add Provider Account**
2. Choose a licensed provider, give the account a name, and (optionally) the external account label
3. Enter the credential fields (these are write-only — they will never be displayed back)
4. Click **Save Account**

The new account is saved with **Credentials = Not tested** and **Sync = Never synced**. iliOS will not contact the provider until you click **Test Credentials**.

## Testing Credentials

Click **Test** on any active account. If the test succeeds, the **Credentials** chip becomes **Verified**. If it fails, the chip becomes **Invalid** and the failure message is shown in the **Last error** column.

## Syncing Sites

The **Sync Sites** button is disabled until **Credentials = Verified**. Once verified, click **Sync Sites** to enumerate the sites available to this account from the provider. Synced sites appear in the **External Sites** tab in the account drawer.

## Updating Credentials

Use the **Update Credentials** action (row menu or drawer) when the underlying provider password or token changes. After updating:

- A new credential version is stored
- The **Credentials** chip resets to **Not tested**
- You must click **Test Credentials** to verify the new values before syncing again

Old credential versions are retained for audit and rollback.

## Archive vs. Delete

Archive is a **safe, reversible** action. The account is hidden by default in lists, but the stored credentials are retained until an explicit purge endpoint is added. Archive does not delete the underlying secret.

## Project / Site Mappings

The **Project / Site Mappings** tab on each account shows how many active mappings reference this account. Mappings themselves are managed inside the project Telemetry tab on each project page, not here.`
  }
];

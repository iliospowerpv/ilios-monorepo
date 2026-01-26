# User Menu Placeholder Pages

This document describes the user profile dropdown menu enhancements and placeholder pages implemented for future account, security, and help functionality.

## What Is Implemented

### User Profile Dropdown Menu
The user dropdown menu (top-right corner) now includes:
1. **Account Settings** - Links to `/account`
2. **Security** - Links to `/security`
3. **Help & Resources** - Links to `/help`
4. **Divider**
5. **Logout** - Existing logout functionality (unchanged)

### Account Settings Page (`/account`)
- **Route**: `/account`
- **File**: `src/pages/Account/AccountSettings.tsx`
- **Current Features**:
  - Read-only display of user name, email, role(s), and company
  - Info banner explaining features are coming in future release
  - Placeholder sections (marked "Coming Soon"):
    - Profile Information
    - Notification Preferences
    - Timezone & Locale
    - Account Deactivation

### Security Page (`/security`)
- **Route**: `/security`
- **File**: `src/pages/Security/SecuritySettings.tsx`
- **Current Features**:
  - Info banner explaining security is centrally managed
  - Placeholder sections (marked "Coming Soon"):
    - Password Management
    - Multi-Factor Authentication
    - Active Sessions
    - Audit Activity

### Help & Resources Page (`/help`)
- **Route**: `/help`
- **File**: `src/pages/Help/HelpResources.tsx`
- **Current Features**:
  - Functional content shell (ready for real content)
  - Four category cards:
    1. **Getting Started**
       - Understanding Projects vs Deals
       - Navigating Portfolio, Companies, and Projects
    2. **Finance & Diligence**
       - How finance readiness works
       - Deal to Project conversion explained
    3. **Operations & Lifecycle**
       - Lifecycle stages explained
       - When modules become active
    4. **FAQs**
       - Empty list with "Content coming soon"
  - Clicking any help article shows snackbar: "Documentation coming soon."

## What Is Intentionally Deferred

### Account Settings
- [ ] Profile editing (name, contact details, photo)
- [ ] Notification preferences configuration
- [ ] Timezone and locale selection
- [ ] Account deactivation workflow

### Security
- [ ] Password reset/change flows
- [ ] Multi-factor authentication setup
- [ ] Active session management
- [ ] Security audit log viewing

### Help & Resources
- [ ] Actual documentation content for each help article
- [ ] Search functionality
- [ ] Video tutorials
- [ ] External helpdesk integration

## How to Extend These Pages

### Adding Account Features
1. Edit `src/pages/Account/AccountSettings.tsx`
2. Replace `ComingSoonSection` components with actual form components
3. Add API calls to `src/api/user.ts` for profile updates
4. Implement validation and save handlers

### Adding Security Features
1. Edit `src/pages/Security/SecuritySettings.tsx`
2. Replace `SecuritySection` components with functional UI
3. Add API endpoints for password change, MFA setup, etc.
4. Consider existing password reset flow at `/password-reset-request`

### Adding Help Content
1. Edit `src/pages/Help/HelpResources.tsx`
2. Update the `helpSections` array with real article content
3. Create individual article pages at `/help/:articleId`
4. Replace snackbar with actual navigation to article detail pages

## Technical Notes

- All pages use existing MUI components and theme styling
- Navigation is handled via React Router
- No new backend models or API endpoints were added
- Pages are accessible to all authenticated users (no role restrictions)
- Back button navigates using `navigate(-1)` for history-aware navigation

## Files Changed

- `src/components/layout/PageHeader/PageHeader.tsx` - Updated dropdown menu
- `src/App.tsx` - Added routes for /account, /security, /help
- `src/pages/Account/AccountSettings.tsx` - New page
- `src/pages/Account/index.ts` - Export file
- `src/pages/Security/SecuritySettings.tsx` - New page
- `src/pages/Security/index.ts` - Export file
- `src/pages/Help/HelpResources.tsx` - New page
- `src/pages/Help/index.ts` - Export file

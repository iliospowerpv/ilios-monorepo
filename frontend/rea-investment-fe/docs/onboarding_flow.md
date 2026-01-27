# Onboarding Flow

## Overview

The onboarding flow provides a guided 3-step wizard that helps users set up Ilios in the correct hierarchy order: **Company → Project → Invite Users**. This creates a streamlined first-time setup experience and supports repeated setup for new companies and projects.

## Flow Steps

### Step 1: Company

**Purpose**: Select or create a company to work with.

**Behavior**:
- If `currentCompanyId` is already set in the Context Bar:
  - Shows the selected company with options to:
    - Continue to Step 2
    - Change to a different company (picker)
    - Create a new company (system admins only)
- If no company is selected:
  - Shows company picker to select from accessible companies
  - Shows "Create Company" option (system admins only)

**Permissions**:
- All users can select from their accessible companies
- Only system users (`is_system_user`) can create new companies

**On Completion**:
- Sets `currentCompanyId` in Context Bar
- Persists wizard state to localStorage
- Advances to Step 2

### Step 2: Project

**Purpose**: Create or select a project under the current company.

**Behavior**:
- Displays the selected company as context
- Toggle between "Create New" and "Select Existing" modes
- Create form includes: Name (required), Address, City, State, Zip
- Select mode shows picker with existing projects under this company

**On Completion**:
- Sets `currentProjectId` in Context Bar (recommended)
- Persists wizard state
- Advances to Step 3

### Step 3: Invite Users (Optional)

**Purpose**: Add users to the company with role assignment.

**Behavior**:
- Clearly marked as optional with skip option
- Defaults company to `currentCompanyId`
- User autocomplete search
- Role selection: Admin, Contributor, Read Only
- Optional project assignment (multi-select, collapsed by default)

**Permissions**:
- Only system users can invite/add users
- Shows read-only explanation for non-admin users

**On Completion**:
- Persists invited user emails
- Advances to Completion screen

### Completion Screen

**Displays**:
- Success message with celebration icon
- Checklist showing:
  - Company configured ✅
  - Project created/selected ✅
  - Users invited ✅ or ☐ (if skipped)

**Navigation Options**:
- Go to Project Overview (canonical `/projects/:projectId`)
- Go to Company Admin
- Back to Home
- Set up another project (clears draft and restarts)

## State Persistence

### Storage Mechanism

Wizard state is persisted to localStorage using a user-specific key:

```
Key: ilios_onboarding_draft_{userId}
```

### Stored Data

```typescript
interface OnboardingDraftState {
  currentStep: 'company' | 'project' | 'invite' | 'complete';
  companyId: number | null;
  companyName: string | null;
  projectId: number | null;
  projectName: string | null;
  invitedUserEmails: string[];
}
```

### Resume Behavior

- On page load, the wizard checks for existing draft state
- If found, resumes from the persisted step
- Validates that required data exists for each step (e.g., Step 2 requires companyId)
- Falls back to appropriate step if data is missing

### Completion Cleanup

- On successful completion, draft state remains until user starts a new setup
- Clicking "Set up another project" clears the draft state entirely

## Context Bar Integration

### Reading Context

The wizard uses `useEntityContext()` to access:
- `currentCompany` - Used as default in Step 1
- `setCurrentCompany()` - Called when company is selected/created
- `setCurrentProject()` - Called when project is selected/created

### Context Updates

| Action | Context Update |
|--------|----------------|
| Select company | `setCurrentCompany({ id, name })` |
| Create company | `setCurrentCompany({ id, name })` |
| Select project | `setCurrentProject({ id, name })` |
| Create project | `setCurrentProject({ id, name })` |

## Entry Points

### Primary Entry

**Home page Quick Actions**:
- Prominent "Set Up a New Project" button with rocket icon
- Navigates to `/onboarding`

### Alternative Entry

Direct navigation to `/onboarding` is always accessible for authenticated users.

## Route Structure

```
/onboarding
  └── OnboardingPage (wizard container)
      ├── CompanyStep
      ├── ProjectStep
      ├── InviteStep
      └── CompletionScreen
```

## Component Architecture

### Hook: `useOnboardingState()`

Central state management hook providing:
- `state` - Current draft state
- `isLoaded` - Whether state has been hydrated from localStorage
- `setCompany(id, name)` - Set company and advance to project step
- `setProject(id, name)` - Set project and advance to invite step
- `addInvitedUser(email)` - Add email to invited list
- `completeOnboarding()` - Mark as complete
- `clearDraft()` - Reset all state
- `resetToStep(step)` - Go back to a previous step

### Components

| Component | Purpose |
|-----------|---------|
| `OnboardingProgress` | Step indicator with completion status |
| `CompanyStep` | Company selection/creation UI |
| `ProjectStep` | Project selection/creation UI |
| `InviteStep` | User invitation UI |
| `CompletionScreen` | Success checklist and navigation |

## Deferred Features

The following features are intentionally not implemented in this initial version:

1. **Company Admin entry point** - Access from Company Admin page (use Home CTA instead)
2. **Projects list entry point** - Access from Projects list (use Home CTA instead)
3. **Email delivery for invitations** - Users are added directly; email notifications not sent
4. **Role-based project assignment** - Project assignment in Step 3 is UI-only; not persisted
5. **Workflow engine** - This is a simple linear wizard, not a generalized workflow system

## Styling

The onboarding flow follows Ilios design patterns:
- Uses MUI components (Card, Button, TextField, Select, etc.)
- Stepper component for progress indication
- Toast/snackbar for success messages
- Alert components for info/warning/error states
- Inline forms (no nested modals)

## File Structure

```
src/modules/onboarding/
├── index.ts                        # Module exports
├── ModuleContainer.tsx             # Auth gate
├── hooks/
│   ├── index.ts
│   └── useOnboardingState.ts       # State persistence hook
├── components/
│   ├── index.ts
│   ├── OnboardingProgress/         # Step indicator
│   ├── CompanyStep/                # Step 1 UI
│   ├── ProjectStep/                # Step 2 UI
│   ├── InviteStep/                 # Step 3 UI
│   └── CompletionScreen/           # Success screen
└── pages/
    ├── index.ts
    └── OnboardingPage/
        └── OnboardingPage.tsx      # Wizard container
```

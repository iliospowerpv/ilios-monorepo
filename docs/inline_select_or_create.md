# Inline Select or Create Pattern

## Overview

The "Select or Create" pattern allows users to either select an existing entity from a dropdown or create a new one inline, without leaving the current workflow or navigating to Settings.

This pattern is implemented as reusable components that can be dropped into any dialog or form where entity selection is needed.

## Components

### SelectOrCreateUser

Located at: `frontend/rea-investment-fe/src/components/forms/SelectOrCreate/SelectOrCreateUser.tsx`

A user picker component with inline creation capability.

**Props:**
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `value` | `number \| null` | required | Currently selected user ID |
| `onChange` | `(userId: number \| null) => void` | required | Callback when selection changes |
| `canCreate` | `boolean` | `true` | Whether to show "Create New..." option |
| `defaultCompanyId` | `number` | - | Default company for new user creation |
| `label` | `string` | `"Select User"` | Input label |
| `required` | `boolean` | `false` | Whether field is required |
| `disabled` | `boolean` | `false` | Whether field is disabled |
| `helperText` | `string` | - | Helper text below input |
| `error` | `boolean` | `false` | Whether to show error state |

**Usage:**
```tsx
import { SelectOrCreateUser } from '../../../../components/forms/SelectOrCreate';

<SelectOrCreateUser
  value={selectedUserId}
  onChange={setSelectedUserId}
  canCreate={hasPermission}
  defaultCompanyId={companyId}
  label="Select User"
  required
/>
```

**Behavior:**
1. Displays an Autocomplete dropdown with existing users
2. Shows a "Create New User..." option at the bottom (if `canCreate=true`)
3. Selecting "Create New..." switches to inline creation mode
4. Creation form includes: Email, First Name, Last Name, Phone (optional)
5. On successful creation, auto-selects the new user and returns to selection mode
6. Back button allows returning to selection without creating

## Where It's Used

### Portfolio Admin Module
- **AddUserDialog** (`/portfolio-admin/components/dialogs/AddUserDialog.tsx`)
  - Used for adding users at portfolio, company, and project levels
  - `canCreate` is always `true` for admin workflows

### Home Module
- **InviteUserDialog** (`/modules/home/pages/Home/dialogs/InviteUserDialog.tsx`)
  - Used for the "Add User" quick action on the home page
  - `defaultCompanyId` is set from the current company context

### Onboarding Module
- **InviteStep** (`/modules/onboarding/components/InviteStep/InviteStep.tsx`)
  - Used during the onboarding flow for inviting team members
  - `canCreate` is gated by user permissions (system admin or company admin)

## Permissions Behavior

The `canCreate` prop controls whether the "Create New..." option appears:

| User Role | canCreate | Behavior |
|-----------|-----------|----------|
| System Admin | `true` | Can create users anywhere |
| Company Admin | `true` | Can create users within their company |
| Contributor | `false` | Can only select existing users |
| Read Only | `false` | Can only select existing users |

Implementation example:
```tsx
const { isSystemUser, isCompanyAdminFull } = useAccess(companyId);
const canCreateUsers = isSystemUser || isCompanyAdminFull;

<SelectOrCreateUser
  canCreate={canCreateUsers}
  // ...
/>
```

## Creation Form Fields

### User Creation (Minimal Fields)
- **Email** (required): User's email address
- **First Name** (required): User's first name
- **Last Name** (required): User's last name
- **Phone** (optional): User's phone number

The created user is assigned:
- Default role: "Read Only"
- Parent company: Uses `defaultCompanyId` prop
- Status: Invited (pending registration)

## Extending the Pattern

### Adding a New SelectOrCreate Component

1. Create a new component in `components/forms/SelectOrCreate/`
2. Follow the same structure as `SelectOrCreateUser`:
   - Accept `value`, `onChange`, `canCreate` props
   - Use `__create_new__` sentinel value for the create option
   - Implement `select` and `create` view modes
   - Auto-select newly created entity after success

3. Export from `components/forms/SelectOrCreate/index.ts`

### Example Template
```tsx
const CREATE_NEW_SENTINEL = '__create_new__';

type ViewMode = 'select' | 'create';

export const SelectOrCreateProject: React.FC<Props> = ({
  value,
  onChange,
  canCreate = true,
  // ...
}) => {
  const [mode, setMode] = useState<ViewMode>('select');
  
  // Handle sentinel selection
  const handleChange = (option) => {
    if (option?.id === CREATE_NEW_SENTINEL) {
      setMode('create');
      return;
    }
    onChange(option?.id ?? null);
  };
  
  if (mode === 'create') {
    return <CreateForm onSuccess={(newId) => {
      onChange(newId);
      setMode('select');
    }} />;
  }
  
  return <Autocomplete ... />;
};
```

## Design Principles

1. **No Modal Stacking**: Use inline expansion within the dialog, never open a second modal
2. **Minimal Fields**: Only required fields for quick creation
3. **Auto-Selection**: New entity is automatically selected after creation
4. **Context Preservation**: User never leaves the current workflow
5. **Permission-Aware**: Create option is hidden when user lacks permission
6. **Error Recovery**: Failed creation shows error inline, doesn't close dialog

## Related Documentation

- [Access Model Audit](./access_model_audit.md) - User access and permission system
- [Context Bar Contract](./context_bar_contract.md) - Entity scope management

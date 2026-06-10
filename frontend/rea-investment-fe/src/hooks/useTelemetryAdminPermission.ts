import { useAuth } from '../contexts/auth/auth';

/**
 * Frontend mirror of the backend `telemetry_admin_required` gate. This is a UX
 * convenience only — every telemetry scheduler/backfill/admin endpoint enforces
 * the same check server-side and remains authoritative. A non-admin who somehow
 * reaches a control still gets a 403 from the API.
 *
 * Grants access to:
 *  - platform-bypass users (system users and global admins), matching the
 *    backend's `has_platform_bypass = is_system_user OR is_global_admin`;
 *  - users whose role carries the `Telemetry` module `admin` permission;
 *  - existing settings administrators (`Settings Page` `edit`), so they don't
 *    silently lose the write access they had before the Telemetry permission
 *    was introduced.
 */
export const useTelemetryAdminPermission = (): boolean => {
  const { user } = useAuth();
  if (!user) return false;
  if (user.is_system_user || user.is_global_admin) return true;
  const perms = user.role?.permissions ?? {};
  const telemetryAdmin = (perms as Record<string, { admin?: boolean }>)['Telemetry']?.admin;
  if (telemetryAdmin) return true;
  const settingsEdit = (perms as Record<string, { edit?: boolean }>)['Settings Page']?.edit;
  return Boolean(settingsEdit);
};

export default useTelemetryAdminPermission;

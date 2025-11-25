import { useAuth } from '../../contexts/auth/auth';

export const useAccess = (companyId?: number) => {
  const { user } = useAuth();

  const isSystemUser = user?.is_system_user;
  const isCompanyAdminFull = user?.role?.permissions?.['Settings Page']?.view;

  const isFullAccess = isSystemUser || isCompanyAdminFull;
  const isUserParentCompany = isSystemUser ? true : user?.parent_company_id === companyId;

  return {
    isSystemUser,
    isCompanyAdminFull,
    isFullAccess,
    isUserParentCompany
  };
};

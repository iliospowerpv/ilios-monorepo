"""Implements customized access to the Diligence module overview page
based on the user role diligence permission and role company type"""

import logging

from fastapi import Depends, HTTPException, status

from app.helpers.authorization import AuthorizedUser, DiligencePermissions
from app.static import PermissionsActions
from app.static.companies import CompanyTypes

logger = logging.getLogger(__name__)


class DiligenceOverviewPagePermissions:
    allowed_company_types = [CompanyTypes.project_site_owner]

    def __call__(self, current_user=Depends(AuthorizedUser(DiligencePermissions(PermissionsActions.view)))):
        """
        First, validate if user has access to the diligence module by diligence permission using permissions-based check.
        Then, check user parent company if it allows overview page access
        """
        # skip extra check for the system user
        if current_user.is_system_user:
            return current_user

        if current_user.role.related_company_type.company_type not in self.allowed_company_types:
            logger.warning(
                f"User with ID <{current_user.id}> (role <{current_user.role.name}>, "
                f"role company type <{current_user.role.related_company_type.company_type.value}>) "
                f"is not allowed to review Due Diligence Overview page"
            )
            raise HTTPException(status.HTTP_403_FORBIDDEN)

        return current_user

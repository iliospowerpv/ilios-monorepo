"""Module includes dependencies which validates company/site entities via project access.

This module now integrates with the Canonical Effective-Access Resolver (Phase B.1)
for portfolio/company/project access hierarchy validation.

AUTHORITATIVE: The resolver is the single source of truth for entity-level access.
No legacy fallback exists - if resolver cannot determine access, it DENIES (fail-closed).
"""

import logging
from typing import Optional, Union

from fastapi import Depends, HTTPException, status

from app.crud.alert import AlertCRUD
from app.crud.company import CompanyCRUD
from app.crud.das_connection import DASConnectionCRUD
from app.crud.device import DeviceCRUD
from app.crud.device_document import DeviceDocumentCRUD
from app.crud.document import DocumentCRUD
from app.crud.file import FileCRUD
from app.crud.site import SiteCRUD
from app.db.session import get_session
from app.helpers.access_resolver import (
    resolve_effective_access,
    EffectiveAccessResult,
    AccessDecision,
    AccessDeniedReason,
)
from app.helpers.authentication import get_current_user
from app.helpers.roles_documents_mapping.handlers_factory import RoleDocumentsHandlerFactory
from app.static import PermissionType

logger = logging.getLogger(__name__)


def validate_entity_exists(entity, entity_id: int, entity_type_name: str):
    if not entity:
        logger.warning(f"There is no {entity_type_name} with id {entity_id}")
        raise HTTPException(status.HTTP_404_NOT_FOUND)


class GetAuthorizedEntity:
    """Return Site/Company if user has access to it.
    
    AUTHORITATIVE: Uses the Canonical Effective-Access Resolver (Phase B.1)
    for all entity-level access checks. No legacy fallback exists.
    
    If resolver cannot determine access (missing context), access is DENIED (fail-closed).
    
    Access is granted via the portfolio/company/project hierarchy:
    - Portfolio access covers all companies in the hub and their projects
    - Company access covers all projects under that company
    - Project access covers only that specific project
    """

    def __init__(
        self,
        company_site_id,
        current_user,
        db_session,
        permission_type: PermissionType,
        additional_company_site_id_access: Union[int, None] = None,
    ):
        """Initialize the entity authorization handler.
        
        Args:
            company_site_id: The ID of the company or site to access
            current_user: The current user object
            db_session: Database session
            permission_type: Whether accessing a company or site
            additional_company_site_id_access: DEPRECATED - This parameter was used
                for legacy fallback logic which has been removed. Company admins now
                get access to sites through company-level grants in the resolver.
                This parameter is ignored but kept for API compatibility.
        """
        self.id = int(company_site_id)
        self.permission_type = permission_type
        self.current_user = current_user
        self.db_session = db_session
        self._access_result: Optional[EffectiveAccessResult] = None
        if additional_company_site_id_access is not None:
            logger.debug(
                f"DEPRECATED: additional_company_site_id_access={additional_company_site_id_access} "
                f"is ignored. Access is resolved via company-level grants."
            )

    def _validate_access_via_resolver(self, entity) -> EffectiveAccessResult:
        """Use the Canonical Effective-Access Resolver to validate access.
        
        AUTHORITATIVE: Always returns a decision (allow/deny), never undetermined.
        If context is missing or error occurs, returns DENY with appropriate reason.
        """
        try:
            if self.permission_type == PermissionType.site:
                company_id = entity.company_id if hasattr(entity, 'company_id') else None
                if not company_id:
                    logger.warning(
                        f"RESOLVER_CONTEXT_MISSING: user_id={self.current_user.id} "
                        f"entity_type=site entity_id={self.id} reason=no_company_id"
                    )
                    return EffectiveAccessResult(
                        decision=AccessDecision.DENY,
                        reason_code=AccessDeniedReason.UNDETERMINED_CONTEXT.value
                    )
                return resolve_effective_access(
                    user_id=self.current_user.id,
                    company_id=company_id,
                    db_session=self.db_session,
                    project_id=self.id
                )
            elif self.permission_type == PermissionType.company:
                return resolve_effective_access(
                    user_id=self.current_user.id,
                    company_id=self.id,
                    db_session=self.db_session,
                    project_id=None
                )
            else:
                logger.warning(
                    f"RESOLVER_CONTEXT_MISSING: user_id={self.current_user.id} "
                    f"entity_type={self.permission_type} entity_id={self.id} reason=unknown_permission_type"
                )
                return EffectiveAccessResult(
                    decision=AccessDecision.DENY,
                    reason_code=AccessDeniedReason.UNDETERMINED_CONTEXT.value
                )
        except Exception as e:
            logger.error(
                f"RESOLVER_SYSTEM_ERROR: user_id={self.current_user.id} "
                f"entity_type={self.permission_type.value} entity_id={self.id} "
                f"exception={type(e).__name__}: {e}",
                exc_info=True
            )
            return EffectiveAccessResult(
                decision=AccessDecision.DENY,
                reason_code=AccessDeniedReason.SYSTEM_ERROR.value
            )

    def _log_access_decision(self, result: EffectiveAccessResult) -> None:
        """Log access decision for auditing."""
        if result.decision == AccessDecision.ALLOW:
            grant_summary = [f"{gs.level}:{gs.role}" for gs in result.grant_sources]
            logger.debug(
                f"ACCESS_GRANTED: user_id={self.current_user.id} "
                f"entity_type={self.permission_type.value} entity_id={self.id} "
                f"effective_role={result.effective_base_role} sources={grant_summary}"
            )
        else:
            logger.warning(
                f"ACCESS_DENIED: user_id={self.current_user.id} "
                f"entity_type={self.permission_type.value} entity_id={self.id} "
                f"reason_code={result.reason_code} "
                f"sources={[gs.level for gs in result.grant_sources]}"
            )

    def _validate_access_given(self, entity=None):
        """Check access was given to user.
        
        AUTHORITATIVE: Uses resolver as the single source of truth.
        No legacy fallback - if resolver denies, access is denied.
        """
        if self.current_user.is_system_user:
            return

        if not entity:
            self._access_result = EffectiveAccessResult(
                decision=AccessDecision.DENY,
                reason_code=AccessDeniedReason.UNDETERMINED_CONTEXT.value
            )
            self._log_access_decision(self._access_result)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {self._access_result.reason_code}"
            )

        self._access_result = self._validate_access_via_resolver(entity)
        self._log_access_decision(self._access_result)

        if self._access_result.decision == AccessDecision.DENY:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {self._access_result.reason_code}"
            )

    def _retrieve_entity(self):
        """Check entity user tried to access exists and return it"""
        entity_handler_mapping = {
            PermissionType.site: SiteCRUD,
            PermissionType.company: CompanyCRUD,
        }
        crud_handler = entity_handler_mapping[self.permission_type](self.db_session)
        entity = crud_handler.get_by_id(self.id)
        validate_entity_exists(entity, self.id, self.permission_type)
        # Move access validation after entity exists check, otherwise 404 will never happen
        # Pass entity to resolver for company_id context
        self._validate_access_given(entity)
        return entity

    def get_authorized_entity(self):
        return self._retrieve_entity()
    
    def get_access_result(self) -> Optional[EffectiveAccessResult]:
        """Return the access result for explainability/auditing."""
        return self._access_result


def get_authorized_company(company_id: int, current_user=Depends(get_current_user), db_session=Depends(get_session)):
    return GetAuthorizedEntity(company_id, current_user, db_session, PermissionType.company).get_authorized_entity()


def get_authorized_site(site_id: int, current_user=Depends(get_current_user), db_session=Depends(get_session)):
    return GetAuthorizedEntity(site_id, current_user, db_session, PermissionType.site).get_authorized_entity()


def get_authorized_site_with_company_admin(
    site_id: int, current_user=Depends(get_current_user), db_session=Depends(get_session)
):
    """Get authorized site with company admin context.
    
    NOTE: This function previously used legacy fallback to grant explicit access.
    With the resolver-based authorization (Phase B.1), company admins get access
    to sites through their company-level grants in the portfolio/company/project
    hierarchy. The additional_company_site_id_access parameter is now deprecated.
    
    Access flow:
    - User with company access -> Can access all sites under that company
    - User with portfolio access -> Can access all sites under all companies in hub
    """
    return GetAuthorizedEntity(
        site_id, current_user, db_session, PermissionType.site
    ).get_authorized_entity()


def get_authorized_alert(alert_id: int, current_user=Depends(get_current_user), db_session=Depends(get_session)):
    alert = AlertCRUD(db_session).get_by_id(alert_id)
    if not alert:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    get_authorized_site(alert.device.site_id, current_user, db_session)
    return alert


def get_authorized_device(
    device_id: int,
    site=Depends(get_authorized_site),
    current_user=Depends(get_current_user),
    db_session=Depends(get_session),
):
    """Ensure user has access to the device based on the site access"""
    device = DeviceCRUD(db_session).get_by_id(device_id)
    validate_entity_exists(device, device_id, "device")
    # validate device belongs to the site from request path
    if device.site_id != site.id:
        logger.warning(
            f"Scope mismatch! "
            f"User {current_user.id} tried to access device {device_id} which attached to different site_id"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    return device


def get_authorized_breadcrumbs_device(
    device_id: int,
    current_user=Depends(get_current_user),
    db_session=Depends(get_session),
):
    """Ensure user has access to the device based and site device belongs to"""
    device = DeviceCRUD(db_session).get_by_id(device_id)
    validate_entity_exists(device, device_id, "device")
    if current_user.is_system_user:
        return device

    # validate device belongs to the user sites
    if device.site_id not in current_user.get_limited_sites_ids():
        logger.warning(
            f"Scope mismatch! "
            f"User {current_user.id} tried to access device {device_id} from the site where user has no access"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    return device


def get_authorized_document(
    document_id: int,
    site=Depends(get_authorized_site),
    current_user=Depends(get_current_user),
    db_session=Depends(get_session),
):
    """For the due diligence module, ensure user has access to the document based on the site access"""
    document = DocumentCRUD(db_session).get_by_id(document_id)
    validate_entity_exists(document, document_id, "document")
    # validate document belongs to the site from request path
    if document.site_id != site.id:
        logger.warning(
            f"Scope mismatch! "
            f"User {current_user.id} tried to access document {document_id} which attached to different site_id"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    if current_user.is_system_user:
        return document

    output_roles_ids = RoleDocumentsHandlerFactory.get_available_roles_by_document(
        document=document, db_session=db_session
    )

    if current_user.role_id not in output_roles_ids:
        logger.warning(
            f"User with ID <{current_user.id}> (role <{current_user.role.name}>, "
            f"role company type <{current_user.role.related_company_type.company_type.value}>) "
            f"is not allowed to access to the document <{document.name.value}> (section <{document.section.name.value}>)"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    return document


def get_authorized_breadcrumbs_document(
    document_id: int,
    current_user=Depends(get_current_user),
    db_session=Depends(get_session),
):
    """For the due diligence module, ensure user has access to the document and site document belongs to"""
    document = DocumentCRUD(db_session).get_by_id(document_id)
    validate_entity_exists(document, document_id, "document")
    if current_user.is_system_user:
        return document

    # validate document belongs to the user sites
    if document.site_id not in current_user.get_limited_sites_ids():
        logger.warning(
            f"Scope mismatch! "
            f"User {current_user.id} tried to access document {document_id} from the site where user has no access"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    return document


def get_authorized_file(
    file_id: int,
    document=Depends(get_authorized_document),
    current_user=Depends(get_current_user),
    db_session=Depends(get_session),
):
    """For the due diligence module, ensure user has access to the file"""
    file_ = FileCRUD(db_session).get_by_id(file_id)
    if not file_ or file_.deleted:
        logger.warning(f"There is no file with id {file_id}")
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    # validate file belongs to the document from request path
    if file_.document_id != document.id:
        logger.warning(
            f"Scope mismatch! "
            f"User {current_user.id} tried to access file {file_id} which attached to different document_id"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    return file_


def get_authorized_device_document(
    document_id: int,
    device=Depends(get_authorized_device),
    current_user=Depends(get_current_user),
    db_session=Depends(get_session),
):
    """For the due diligence module, ensure user has access to the file"""
    device_document = DeviceDocumentCRUD(db_session).get_by_id(document_id)
    validate_entity_exists(device_document, document_id, "device document")
    # validate file belongs to the device from request path
    if device_document.device_id != device.id:
        logger.warning(
            f"Scope mismatch! "
            f"User {current_user.id} tried to access device document {document_id} which attached to different device"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    return device_document


def get_authorized_connection(
    connection_id: int,
    company=Depends(get_authorized_company),
    current_user=Depends(get_current_user),
    db_session=Depends(get_session),
):
    """For the DAS connection ensure user has access to the connection"""
    das_connection = DASConnectionCRUD(db_session).get_by_id(connection_id)
    validate_entity_exists(das_connection, connection_id, "das connection")
    # validate connection belongs to the company from request path
    if das_connection.company_id != company.id:
        logger.warning(
            f"Scope mismatch! "
            f"User {current_user.id} tried to access das connection {connection_id} "
            "which attached to different company"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    return das_connection

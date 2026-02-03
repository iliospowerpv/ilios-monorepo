"""Module includes dependencies which validates company/site entities via project access.

This module now integrates with the Canonical Effective-Access Resolver (Phase B)
for portfolio/company/project access hierarchy validation.
"""

# TODO consider refactoring into smaller pieces
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
from app.helpers.access_resolver import resolve_effective_access, EffectiveAccessResult
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
    
    Now integrates with the Canonical Effective-Access Resolver (Phase B)
    to validate access using the portfolio/company/project hierarchy.
    """

    def __init__(
        self,
        company_site_id,
        current_user,
        db_session,
        permission_type: PermissionType,
        additional_company_site_id_access: Union[int, None] = None,
    ):
        # Make sure company_site_id is integer. When shared as a dependent parameter from API it is str.
        self.id = int(company_site_id)
        self.permission_type = permission_type
        self.current_user = current_user
        self.db_session = db_session
        # additional_company_site_id_access is parameter to explicitly give access for the user
        # to the specific site/company, which is utilized to provide company admin ability to manipulate
        # attached to the parent company sources
        self.additional_company_site_id_access = additional_company_site_id_access
        # Store access result for explainability
        self._access_result: Optional[EffectiveAccessResult] = None

    def _validate_access_via_resolver(self, entity) -> Optional[bool]:
        """Use the Canonical Effective-Access Resolver to validate access.
        
        Returns:
            True: Access granted by resolver (authoritative)
            False: Access denied by resolver (authoritative - no fallback)
            None: Resolver could not determine (missing context - use legacy)
        """
        try:
            if self.permission_type == PermissionType.site:
                # For site access, use project-level resolution
                company_id = entity.company_id if hasattr(entity, 'company_id') else None
                if company_id:
                    self._access_result = resolve_effective_access(
                        user_id=self.current_user.id,
                        company_id=company_id,
                        db_session=self.db_session,
                        project_id=self.id
                    )
                    # Return actual result - resolver is authoritative
                    return self._access_result.is_allowed
                else:
                    # No company_id context - can't use resolver
                    return None
            elif self.permission_type == PermissionType.company:
                # For company access, use company-level resolution
                self._access_result = resolve_effective_access(
                    user_id=self.current_user.id,
                    company_id=self.id,
                    db_session=self.db_session,
                    project_id=None
                )
                # Return actual result - resolver is authoritative
                return self._access_result.is_allowed
        except Exception as e:
            logger.warning(f"Resolver check failed with exception: {e}")
            # Exception during resolution - can't determine, use legacy
            return None
        return None

    def _validate_access_given(self, entity=None):
        """Check access was given to user.
        
        Uses the Canonical Effective-Access Resolver as the authoritative source.
        Only falls back to legacy check when resolver cannot determine access
        (missing context or resolver error).
        """
        if self.current_user.is_system_user:
            return

        # Use resolver as authoritative source when entity context is available
        if entity:
            resolver_result = self._validate_access_via_resolver(entity)
            
            if resolver_result is True:
                # Resolver granted access - authoritative decision
                logger.debug(
                    f"User {self.current_user.id} granted access to {self.permission_type} {self.id} "
                    f"via resolver. Sources: {self._access_result.grant_sources if self._access_result else 'N/A'}"
                )
                return
            
            if resolver_result is False:
                # Resolver denied access - authoritative decision, no fallback
                denied_reason = self._access_result.denied_reason if self._access_result else "resolver_denied"
                logger.warning(
                    f"User {self.current_user.id} denied access to {self.permission_type} {self.id} "
                    f"by resolver. Reason: {denied_reason}"
                )
                raise HTTPException(status.HTTP_403_FORBIDDEN)
            
            # resolver_result is None - resolver couldn't determine, use legacy
            logger.debug(f"Resolver could not determine access, falling back to legacy check")

        # Legacy fallback (only when resolver can't determine - not after denial)
        if self.permission_type == PermissionType.company:
            user_data = [company.id for company in self.current_user.companies]
            # TODO think about rewrite it with <additional_company_site_id_access> usage,
            #  rather than provide full access for the company management
            user_data.append(self.current_user.parent_company_id)
        else:
            user_data = [site.id for site in self.current_user.sites]

        if self.additional_company_site_id_access:
            user_data.append(self.additional_company_site_id_access)

        if self.id not in user_data:
            logger.warning(
                f"User {self.current_user.id} tried to access {self.permission_type} {self.id} "
                f"without {self.permission_type} access (legacy check)."
            )
            raise HTTPException(status.HTTP_403_FORBIDDEN)

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
    """Patch current user object to provide access to the specific site explicitly"""
    return GetAuthorizedEntity(
        site_id, current_user, db_session, PermissionType.site, additional_company_site_id_access=site_id
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

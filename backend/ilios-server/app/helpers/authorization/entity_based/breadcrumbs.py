import logging

from fastapi import Depends, HTTPException, status

from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization import get_authorized_breadcrumbs_task, get_authorized_company, get_authorized_site
from app.helpers.authorization.project_access import (
    get_authorized_breadcrumbs_device,
    get_authorized_breadcrumbs_document,
)
from app.static import BreadcrumbsEntityTypes

logger = logging.getLogger(__name__)


BREADCRUMBS_ENTITY_TYPE_MAPPER = {
    # Mapper to get authorization method related to entity type and attribute name for parent object ID
    BreadcrumbsEntityTypes.company: (get_authorized_company, None),
    BreadcrumbsEntityTypes.site: (get_authorized_site, "company_id"),
    BreadcrumbsEntityTypes.device: (get_authorized_breadcrumbs_device, "site_id"),
    BreadcrumbsEntityTypes.document: (get_authorized_breadcrumbs_document, "site_id"),
    BreadcrumbsEntityTypes.task: (get_authorized_breadcrumbs_task, "board_id"),
}


def get_authorized_breadcrumbs_entity(
    entity_id: int,
    entity_type: BreadcrumbsEntityTypes,
    current_user=Depends(get_current_user),
    db_session=Depends(get_session),
):
    authorization_method, parent_attr_name = BREADCRUMBS_ENTITY_TYPE_MAPPER.get(entity_type, (None, None))
    if not authorization_method:
        logger.warning(f"There is no authorization method for entity type {entity_type}")
        raise HTTPException(status_code=status.HTTP_400, detail="Invalid entity type")
    entity = authorization_method(entity_id, current_user, db_session)
    if parent_attr_name:
        entity.parent_id = getattr(entity, parent_attr_name, None)
        entity.parent_entity_type = parent_attr_name.split("_")[0]
    else:
        entity.parent_id = None
        entity.parent_entity_type = None
    return entity

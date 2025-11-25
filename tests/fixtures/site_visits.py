from copy import deepcopy

import pytest

from app.crud.site_visit import SiteVisitCRUD
from app.crud.sv_uploads import SiteVisitUploadCRUD
from app.static.site_visits import SiteVisitsUploads
from tests.unit import samples


@pytest.fixture(scope="function")
def site_visit(db_session, site_om_task):
    """Applicable only for the O&M site level tasks"""
    crud_ = SiteVisitCRUD(db_session)

    payload = deepcopy(samples.TEST_SITE_VISIT_PAYLOAD)
    payload.update({"task_id": site_om_task.id})

    site_visit_object = crud_.create_item(payload)

    yield site_visit_object

    crud_.delete_by_id(site_visit_object.id)


@pytest.fixture(scope="function", params=[SiteVisitsUploads.site_conditions.value])
def site_visit_upload(db_session, site_visit, request):
    """Attachment of the specific type"""
    section_name = request.param
    payload = {
        "filepath": "test/file/path",
        "filename": samples.TEST_SITE_VISIT_UPLOAD_NAME,
        "site_visit_id": site_visit.id,
        "section_name": section_name,
    }

    crud_ = SiteVisitUploadCRUD(db_session)

    obj_ = crud_.create_item(payload)

    yield obj_

    crud_.delete_by_id(obj_.id)

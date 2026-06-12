import copy
from datetime import datetime, timezone

import pytest

import tests.unit.samples as samples
from app.crud.document_key import DocumentKeyCRUD
from app.crud.file import FileCRUD
from app.crud.role import RoleCRUD
from app.models.file import AIParsingResult, FileParsingStatuses
from app.models.project_facts import CanonicalField, FactStatus, ProjectFact
from tests.utils import remove_dynamic_fields, set_user_site_access


class TestDocuments:
    """Tests for due diligence requirements (documents) routes."""

    @staticmethod
    def _generate_list_endpoint(site_id_):
        """/api/due-diligence/SITE_ID/documents"""
        return f"/api/due-diligence/{site_id_}/documents"

    def _generate_individual_endpoint(self, site_id_, document_id_):
        """/api/due-diligence/SITE_ID/documents/DOCUMENT_ID"""
        return f"{self._generate_list_endpoint(site_id_)}/{document_id_}"

    def _generate_description_endpoint(self, site_id_, document_id_):
        """/api/due-diligence/SITE_ID/documents/DOCUMENT_ID/description"""
        return f"{self._generate_individual_endpoint(site_id_, document_id_)}/description"

    def _generate_key_endpoint(self, site_id_, document_id_):
        """/api/due-diligence/SITE_ID/documents/DOCUMENT_ID/keys"""
        return f"{self._generate_individual_endpoint(site_id_, document_id_)}/keys"

    def _generate_details_endpoint(self, site_id_, document_id_):
        """/api/due-diligence/SITE_ID/documents/DOCUMENT_ID/details"""
        return f"{self._generate_individual_endpoint(site_id_, document_id_)}/details"

    def test_get_document_403(self, client, site_id, non_system_user_auth_header):
        """Test that user cannot access the documents if they don't have access to the site"""

        response = client.get(self._generate_individual_endpoint(site_id, 456), headers=non_system_user_auth_header)

        assert response.status_code == 403

    def test_get_document_404(self, client, site_id, company_member_user_auth_header, mocker):
        """Regular 404 handling - document doesn't exist"""
        logger_mock = mocker.patch("app.helpers.authorization.project_access.logger")

        response = client.get(self._generate_individual_endpoint(site_id, 123), headers=company_member_user_auth_header)

        assert response.status_code == 404
        logger_mock.warning.assert_called_with("There is no document with id 123")

    def test_get_document_404_no_site(self, client, site_id, system_user_auth_header, mocker):
        """Unusual 404 handling (now we have the case only for system user) - site doesn't exist"""
        logger_mock = mocker.patch("app.helpers.authorization.project_access.logger")
        site_id = site_id + 1

        response = client.get(self._generate_individual_endpoint(site_id, 123), headers=system_user_auth_header)

        assert response.status_code == 404
        logger_mock.warning.assert_called_with(f"There is no site with id {site_id}")

    def test_get_document_success(
        self, client, api_site, company_member_user_auth_header, company_member_user, db_session
    ):
        set_user_site_access(db_session, api_site, company_member_user)
        # Make sure document is 'Site Lease' otherwise in some moments test fails with different document type
        document = [site_doc for site_doc in api_site.documents if site_doc.name.value == "Site Lease"][0]
        document_default_board = document.task.board

        response = client.get(
            self._generate_individual_endpoint(api_site.id, document.id), headers=company_member_user_auth_header
        )
        expected_due_date = datetime.today().replace(month=12, day=31).strftime("%Y-%m-%d")

        assert response.status_code == 200
        assert response.json() == {
            "id": document.id,
            "name": document.name.value,
            "section": {"id": document.section.id, "name": document.section.name.value},
            "description": None,
            "type": "Diligence",
            "site": {"name": samples.TEST_SITE_NAME, "address": samples.TEST_SITE_ADDRESS, "id": api_site.id},
            "approver": None,
            "task": {
                "assignee": None,
                "due_date": expected_due_date,
                "priority": "Medium",
                "status": {"id": document.task.status_id, "name": document.task.status.name},
                "name": document.name.value,
                "board_id": document_default_board.id,
                "id": document.task.id,
            },
            "display_working_zone": True,
        }

    def test_update_document_description_success(
        self, client, api_site, company_member_user_auth_header, db_session, company_member_user
    ):
        """Validate that description can be set/unset(set to null)"""
        # set access to the api site separately
        set_user_site_access(db_session, api_site, company_member_user)
        document = api_site.documents[0]
        test_description = "This is test due diligence document description"

        # retrieve description to ensure it's empty
        get_response = client.get(
            self._generate_individual_endpoint(api_site.id, document.id), headers=company_member_user_auth_header
        )
        description_before_update = get_response.json()["description"]

        # set description as a non-empty string
        update_response_non_null = client.post(
            self._generate_description_endpoint(api_site.id, document.id),
            headers=company_member_user_auth_header,
            json={"description": test_description},
        )
        get_response = client.get(
            self._generate_individual_endpoint(api_site.id, document.id), headers=company_member_user_auth_header
        )
        description_not_null = get_response.json()["description"]

        # nullify the description
        update_response_set_null = client.post(
            self._generate_description_endpoint(api_site.id, document.id),
            headers=company_member_user_auth_header,
            json={"description": None},
        )
        get_response = client.get(
            self._generate_individual_endpoint(api_site.id, document.id), headers=company_member_user_auth_header
        )
        description_set_null = get_response.json()["description"]

        assert update_response_non_null.status_code == 202
        assert update_response_set_null.status_code == 202
        assert description_before_update is None
        assert description_not_null == test_description
        assert description_set_null is None

    def test_update_document_description_wrong_len(self, client, site, documents, company_member_user_auth_header):
        """Validate that description max len is 200 characters"""
        document = site.documents[0]
        test_description = "*" * 201

        response = client.post(
            self._generate_description_endpoint(site.id, document.id),
            headers=company_member_user_auth_header,
            json={"description": test_description},
        )

        assert response.status_code == 422
        assert (
            response.json()["message"]
            == "Validation error: body.description - String should have at most 200 characters"
        )

    def test_get_site_documents(
        self, client, api_site, documents, file, company_member_user, company_member_user_auth_header, db_session
    ):
        """Validate documents are properly nested and have all the fields"""
        set_user_site_access(db_session, api_site, company_member_user)
        response = client.get(self._generate_list_endpoint(api_site.id), headers=company_member_user_auth_header)
        response_json = response.json()
        # remove IDs as they are dynamic
        response_items_without_ids = copy.deepcopy(response_json["items"])
        remove_dynamic_fields(response_items_without_ids)

        assert response.status_code == 200
        assert response_items_without_ids == samples.EXPECTED_DOCUMENTS_RESPONSE

    @pytest.mark.parametrize(
        # note - roles with unique name chosen for the tests simplicity
        "target_role_name,expected_response",
        (
            # no limit applies - company admin is linked with project/site owner company
            ("Company Admin", samples.EXPECTED_DOCUMENTS_RESPONSE_ALL_SITES_DOCUMENTS),
            # no limit applies - system user has no role, but can view all the documents
            (None, samples.EXPECTED_DOCUMENTS_RESPONSE_ALL_SITES_DOCUMENTS),
            # limited documents views
            ("Construction Manager", samples.EXPECTED_DOCUMENTS_RESPONSE_CONSTRUCTION_MANAGER),
        ),
    )
    def test_get_site_documents_limited_access(
        self,
        client,
        site_id,
        all_site_documents,
        company_member_user,
        company_member_user_auth_header,
        db_session,
        target_role_name,
        expected_response,
        system_user_auth_header,
    ):
        """Validate documents list is limited according to the role-based config"""
        # change user role
        if target_role_name:
            all_roles = RoleCRUD(db_session).get(skip_pagination=True)
            target_role = [role for role in all_roles if role.name == target_role_name][0]
            company_member_user.role_id = target_role.id
            db_session.commit()
            db_session.refresh(company_member_user)

        # choose which token to use
        auth_header = company_member_user_auth_header if target_role_name else system_user_auth_header

        response = client.get(self._generate_list_endpoint(site_id), headers=auth_header)
        response_json = response.json()

        # drop all fields except section/subsection/document names for the structure validation
        response_items_without_ids = copy.deepcopy(response_json["items"])
        remove_dynamic_fields(response_items_without_ids)
        remove_dynamic_fields(response_items_without_ids, field_name="completed_tasks_percentage")
        remove_dynamic_fields(response_items_without_ids, field_name="files_count")
        remove_dynamic_fields(response_items_without_ids, field_name="status")
        remove_dynamic_fields(response_items_without_ids, field_name="assignee")
        remove_dynamic_fields(response_items_without_ids, field_name="ai_supported")

        assert response.status_code == 200
        assert response_items_without_ids == expected_response

    def test_get_site_documents_file_was_deleted(
        self, client, api_site, documents, file, company_member_user_auth_header, db_session, company_member_user
    ):
        set_user_site_access(db_session, api_site, company_member_user)
        FileCRUD(db_session).update_by_id(file.id, {"deleted": True})
        response = client.get(self._generate_list_endpoint(api_site.id), headers=company_member_user_auth_header)
        response_json = response.json()
        executive_summary_section = response_json["items"][0]

        assert response.status_code == 200
        assert executive_summary_section["name"] == samples.EXECUTIVE_SUMMARY_SECTION_NAME
        assert executive_summary_section["documents"][0]["files_count"] == 0

    def test_get_site_documents_404(self, client, company_member_user_auth_header):
        response = client.get(self._generate_list_endpoint(1234), headers=company_member_user_auth_header)
        assert response.status_code == 404

    def test_get_site_documents_403(self, client, site_id, non_system_user_auth_header):
        response = client.get(self._generate_list_endpoint(site_id), headers=non_system_user_auth_header)
        assert response.status_code == 403

    def test_create_document(self, client, document_section, site, file, company_member_user_auth_header, db_session):
        document_payload = copy.deepcopy(samples.CREATE_DOCUMENT_PAYLOAD)
        document_payload.update({"site_id": site.id, "section_id": document_section.id})
        # create snapshot of site documents before the change
        site_documents_before_adding = site.documents

        response = client.post(
            self._generate_list_endpoint(site.id), json=document_payload, headers=company_member_user_auth_header
        )
        # ensure we have the latest instance of the site object
        db_session.refresh(site)
        added_document = [site_doc for site_doc in site.documents if site_doc not in site_documents_before_adding][0]
        assert response.status_code == 200
        assert response.json()["message"] == "Document has been successfully created"
        # validate new document was created
        assert len(site.documents) - len(site_documents_before_adding) == 1
        # validate default board and task was created for document
        assert added_document.task.board

    @pytest.mark.parametrize(
        "field_name,invalid_value,error_code,expected_error_message",
        (
            ("name", "Invalid name", 422, samples.INVALID_DOCUMENT_NAME_ERROR_MSG),
            ("name", "Flow of Funds", 422, samples.INVALID_SECTION_DOCUMENT_NAME_ERROR_MSG),
        ),
    )
    def test_create_document_invalid_payload(
        self,
        client,
        site,
        documents,
        file,
        company_member_user_auth_header,
        field_name,
        invalid_value,
        error_code,
        expected_error_message,
        document_section,
    ):
        document_payload = copy.deepcopy(samples.CREATE_DOCUMENT_PAYLOAD)
        document_payload.update({"site_id": site.id, "section_id": document_section.id})
        document_payload[field_name] = invalid_value

        response = client.post(
            self._generate_list_endpoint(site.id), json=document_payload, headers=company_member_user_auth_header
        )

        assert response.status_code == error_code
        assert response.json()["message"] == expected_error_message

    def test_create_document_404(self, client, company_member_user_auth_header):
        response = client.post(self._generate_list_endpoint(1234), headers=company_member_user_auth_header)
        assert response.status_code == 404

    def test_create_document_403(self, client, site_id, non_system_user_auth_header):
        response = client.post(self._generate_list_endpoint(site_id), headers=non_system_user_auth_header)
        assert response.status_code == 403

    def test_delete_document(self, client, site_id, document, company_member_user_auth_header):
        response = client.delete(
            self._generate_individual_endpoint(site_id, document.id), headers=company_member_user_auth_header
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Document has been successfully removed"

    def test_delete_document_404(self, client, site_id, document, company_member_user_auth_header):
        response = client.delete(
            self._generate_individual_endpoint(site_id, 1234), headers=company_member_user_auth_header
        )
        assert response.status_code == 404

    def test_delete_document_403(self, client, site_id, document, non_system_user_auth_header):
        response = client.delete(
            self._generate_individual_endpoint(site_id, document.id), headers=non_system_user_auth_header
        )
        assert response.status_code == 403

    def test_set_document_key_404(self, client, site_id, document, company_member_user_auth_header):
        response = client.put(self._generate_key_endpoint(site_id, 1234), headers=company_member_user_auth_header)
        assert response.status_code == 404

    def test_set_document_key_403(self, client, site_id, document, non_system_user_auth_header):
        response = client.put(self._generate_key_endpoint(site_id, document.id), headers=non_system_user_auth_header)
        assert response.status_code == 403

    @pytest.mark.parametrize(
        "payload,expected_error_message",
        (
            # empty payload
            ({}, samples.EMPTY_KEY_PAYLOAD_ERR),
            # validate requirements to the value field
            ({"name": "Owner", "value": ""}, samples.KEY_VALUE_TOO_SHORT_ERR),
            ({"name": "Owner", "value": "*" * 2001}, samples.KEY_VALUE_TOO_LONG_ERR),
            # unexpected key value/key not allowed for the document type
            ({"name": "Owner", "value": "test"}, samples.KEY_NOT_ALLOWED_FOR_DOCUMENT_KIND_ERR),
        ),
    )
    def test_set_document_key_invalid_payload(
        self, client, site_id, document, company_member_user_auth_header, payload, expected_error_message
    ):
        response = client.put(
            self._generate_key_endpoint(site_id, document.id), headers=company_member_user_auth_header, json=payload
        )
        assert response.status_code == 422
        assert response.json()["message"] == expected_error_message

    @pytest.mark.parametrize(
        "api_calls_number,auth_header_getter,expected_log_message_action",
        (
            # call API once to create key
            (1, lambda system_user_auth_header, company_member_user_auth_header: system_user_auth_header, "created"),
            # call API several times to update key
            (
                2,
                lambda system_user_auth_header, company_member_user_auth_header: company_member_user_auth_header,
                "updated",
            ),
        ),
    )
    def test_set_document_key_success(
        self,
        client,
        site_id,
        site_lease_document,
        system_user_auth_header,
        company_member_user_auth_header,
        api_calls_number,
        auth_header_getter,
        expected_log_message_action,
        mocker,
    ):
        """For the site lease document, validate key can be set twice - added and updated"""
        logger_mock = mocker.patch("app.routers.due_diligence.documents.logger")
        updated_key_name = "Quiet Enjoyment"
        expected_log_message = (
            f"Key <{updated_key_name}> has been {expected_log_message_action} for the document "
            f"'{site_lease_document.id}'"
        )
        payload = {"name": updated_key_name, "value": "Test"}

        for _ in range(api_calls_number):
            put_response = client.put(
                self._generate_key_endpoint(site_id, site_lease_document.id),
                headers=auth_header_getter(system_user_auth_header, company_member_user_auth_header),
                json=payload,
            )
            assert put_response.status_code == 202
        logger_mock.info.assert_called_with(expected_log_message)

    def test_update_document_detail_success(
        self, client, api_site, company_member_user_auth_header, db_session, company_member_user
    ):
        """Validate document approver can be set/unset"""
        company_member_user.is_registered = True
        db_session.commit()
        # set access to the api site separately
        set_user_site_access(db_session, api_site, company_member_user)
        document = api_site.documents[0]

        update_response_non_null = client.post(
            self._generate_details_endpoint(api_site.id, document.id),
            headers=company_member_user_auth_header,
            json={"approver_id": company_member_user.id},
        )
        get_response = client.get(
            self._generate_individual_endpoint(api_site.id, document.id), headers=company_member_user_auth_header
        )
        approver_not_null = get_response.json()["approver"]

        update_response_set_null = client.post(
            self._generate_details_endpoint(api_site.id, document.id),
            headers=company_member_user_auth_header,
            json={},
        )
        get_response = client.get(
            self._generate_individual_endpoint(api_site.id, document.id), headers=company_member_user_auth_header
        )
        approver_null = get_response.json()["approver"]

        assert update_response_non_null.status_code == 202
        assert update_response_set_null.status_code == 202
        assert approver_not_null == {
            "id": company_member_user.id,
            "first_name": company_member_user.first_name,
            "last_name": company_member_user.last_name,
        }
        assert approver_null is None

    def test_update_document_detail_invalid_payload(
        self, client, api_site, company_member_user_auth_header, db_session, company_member_user
    ):
        set_user_site_access(db_session, api_site, company_member_user)
        document = api_site.documents[0]

        response = client.post(
            self._generate_details_endpoint(api_site.id, document.id),
            headers=company_member_user_auth_header,
            json={"approver_id": company_member_user.id + 1},
        )

        assert response.status_code == 400
        assert response.json()["message"] == "Invalid approver ID"

    def test_update_document_detail_no_task(
        self,
        client,
        company_member_user_auth_header,
        site_lease_document,
    ):
        response = client.post(
            self._generate_details_endpoint(site_lease_document.site_id, site_lease_document.id),
            headers=company_member_user_auth_header,
            json={"approver_id": 1},
        )

        assert response.status_code == 412
        assert response.json()["message"] == "Cannot associate document with task"


class TestSetKeyOverrideGuardrail:
    """DD V2 Phase 1.5 — server-side override guardrail + audit integrity for ``set_key``.

    The guardrail must fire on *value divergence* from the AI-extracted original for
    baseline-driving fields, regardless of the client-sent ``status`` — closing the prior
    bypass where sending ``status="accepted"`` skipped the rationale requirement.
    """

    BASELINE_KEY = "Module Wattage"
    CANONICAL_NAME = "module_wattage"

    @staticmethod
    def _key_endpoint(site_id_, document_id_):
        return f"/api/due-diligence/{site_id_}/documents/{document_id_}/keys"

    @staticmethod
    def _patch_allowed_keys(monkeypatch, allowed):
        # Registry is not seeded in the test DB (create_all, no Alembic) and config fallback
        # is off, so the allowed-keys set must be supplied explicitly.
        monkeypatch.setattr(
            "app.routers.due_diligence.documents.AIParsingHandler.get_keys_by_document_type",
            lambda self, document_type: list(allowed),
        )

    @staticmethod
    def _make_canonical_field(db_session, name, display):
        # db_session is session-scoped with no rollback between tests and canonical_fields.name
        # is UNIQUE, so this must be get-or-create to avoid poisoning the shared session.
        field = db_session.query(CanonicalField).filter_by(name=name).first()
        if field is not None:
            return field
        field = CanonicalField(name=name, display_name=display, field_type="text", is_active=True)
        db_session.add(field)
        db_session.commit()
        db_session.refresh(field)
        return field

    @staticmethod
    def _make_candidate_fact(db_session, site_id, canonical_field_id, file_id, value, ai_value):
        fact = ProjectFact(
            site_id=site_id,
            canonical_field_id=canonical_field_id,
            value={"v": value} if value is not None else None,
            ai_extracted_value={"v": ai_value} if ai_value is not None else None,
            status=FactStatus.candidate.value,
            source_file_id=file_id,
        )
        db_session.add(fact)
        db_session.commit()
        db_session.refresh(fact)
        return fact

    def test_baseline_divergence_without_notes_is_rejected(
        self, client, site_id, document, file, db_session, company_member_user_auth_header, monkeypatch
    ):
        """Changed baseline value + status=accepted + no rationale -> 422 (bypass closed)."""
        self._patch_allowed_keys(monkeypatch, [self.BASELINE_KEY])
        field = self._make_canonical_field(db_session, self.CANONICAL_NAME, self.BASELINE_KEY)
        self._make_candidate_fact(db_session, document.site_id, field.id, file.id, "100", "100")

        response = client.put(
            self._key_endpoint(site_id, document.id),
            headers=company_member_user_auth_header,
            json={"name": self.BASELINE_KEY, "value": "999", "file_id": file.id, "status": "accepted"},
        )

        assert response.status_code == 422
        assert "override_notes" in response.json()["message"]
        # Nothing persisted on rejection.
        assert (
            DocumentKeyCRUD(db_session).get_document_key(
                name=self.BASELINE_KEY, document_id=document.id, file_id=file.id
            )
            is None
        )

    def test_baseline_divergence_with_notes_is_saved_as_override(
        self, client, site_id, document, file, db_session, company_member_user_auth_header, monkeypatch
    ):
        """Changed baseline value + rationale -> persisted as overridden even if client said accepted."""
        self._patch_allowed_keys(monkeypatch, [self.BASELINE_KEY])
        field = self._make_canonical_field(db_session, self.CANONICAL_NAME, self.BASELINE_KEY)
        self._make_candidate_fact(db_session, document.site_id, field.id, file.id, "100", "100")

        response = client.put(
            self._key_endpoint(site_id, document.id),
            headers=company_member_user_auth_header,
            json={
                "name": self.BASELINE_KEY,
                "value": "999",
                "file_id": file.id,
                "status": "accepted",
                "override_notes": "Corrected per manufacturer datasheet",
            },
        )

        assert response.status_code == 202
        saved = DocumentKeyCRUD(db_session).get_document_key(
            name=self.BASELINE_KEY, document_id=document.id, file_id=file.id
        )
        assert saved.status == "overridden"
        assert saved.override_notes == "Corrected per manufacturer datasheet"
        assert saved.overridden_by_id is not None
        assert saved.overridden_at is not None
        assert saved.override_value == "999"

    def test_baseline_value_matching_ai_is_accepted_without_notes(
        self, client, site_id, document, file, db_session, company_member_user_auth_header, monkeypatch
    ):
        """Submitting the AI value unchanged -> accepted, no rationale, no override metadata."""
        self._patch_allowed_keys(monkeypatch, [self.BASELINE_KEY])
        field = self._make_canonical_field(db_session, self.CANONICAL_NAME, self.BASELINE_KEY)
        self._make_candidate_fact(db_session, document.site_id, field.id, file.id, "100", "100")

        response = client.put(
            self._key_endpoint(site_id, document.id),
            headers=company_member_user_auth_header,
            json={"name": self.BASELINE_KEY, "value": "100", "file_id": file.id},
        )

        assert response.status_code == 202
        saved = DocumentKeyCRUD(db_session).get_document_key(
            name=self.BASELINE_KEY, document_id=document.id, file_id=file.id
        )
        assert saved.status == "accepted"
        assert saved.override_notes is None
        assert saved.overridden_by_id is None
        assert saved.override_value is None

    def test_non_baseline_field_change_is_allowed_without_notes(
        self, client, site_id, document, file, db_session, company_member_user_auth_header, monkeypatch
    ):
        """Non-baseline fields are unaffected by the guardrail (existing behavior preserved)."""
        self._patch_allowed_keys(monkeypatch, ["Quiet Enjoyment"])

        response = client.put(
            self._key_endpoint(site_id, document.id),
            headers=company_member_user_auth_header,
            json={"name": "Quiet Enjoyment", "value": "Materially changed text", "file_id": file.id},
        )

        assert response.status_code == 202
        saved = DocumentKeyCRUD(db_session).get_document_key(
            name="Quiet Enjoyment", document_id=document.id, file_id=file.id
        )
        assert saved.status == "accepted"

    def test_null_ai_extracted_value_does_not_crash(
        self, client, site_id, document, file, db_session, company_member_user_auth_header, monkeypatch
    ):
        """A candidate fact with NULL ai_extracted_value and no run -> fail-safe, no 500."""
        self._patch_allowed_keys(monkeypatch, [self.BASELINE_KEY])
        field = self._make_canonical_field(db_session, self.CANONICAL_NAME, self.BASELINE_KEY)
        self._make_candidate_fact(db_session, document.site_id, field.id, file.id, "100", None)

        response = client.put(
            self._key_endpoint(site_id, document.id),
            headers=company_member_user_auth_header,
            json={"name": self.BASELINE_KEY, "value": "150", "file_id": file.id},
        )

        # Brand-new key with AI original undeterminable -> not treated as an override.
        assert response.status_code == 202
        saved = DocumentKeyCRUD(db_session).get_document_key(
            name=self.BASELINE_KEY, document_id=document.id, file_id=file.id
        )
        assert saved.status == "accepted"

    def test_run_fallback_divergence_is_rejected(
        self, client, site_id, document, file, db_session, company_member_user_auth_header, monkeypatch
    ):
        """With no candidate fact, the latest completed parse run supplies the AI original."""
        self._patch_allowed_keys(monkeypatch, [self.BASELINE_KEY])
        self._make_canonical_field(db_session, self.CANONICAL_NAME, self.BASELINE_KEY)
        run = AIParsingResult(
            file_id=file.id,
            status=FileParsingStatuses.completed,
            parsed_result={self.CANONICAL_NAME: {"value": "100"}},
            extraction_run_number=1,
        )
        db_session.add(run)
        db_session.commit()

        response = client.put(
            self._key_endpoint(site_id, document.id),
            headers=company_member_user_auth_header,
            json={"name": self.BASELINE_KEY, "value": "999", "file_id": file.id},
        )

        assert response.status_code == 422
        assert "override_notes" in response.json()["message"]

    def test_existing_key_fail_safe_blocks_silent_change(
        self, client, site_id, document, file, db_session, company_member_user_auth_header, monkeypatch
    ):
        """AI original undeterminable + an EXISTING stored value -> any change still needs a rationale."""
        self._patch_allowed_keys(monkeypatch, [self.BASELINE_KEY])
        # Canonical field exists, but there is NO candidate fact and NO completed run, so
        # resolve_ai_original_value returns undetermined and the fail-safe branch engages.
        self._make_canonical_field(db_session, self.CANONICAL_NAME, self.BASELINE_KEY)
        DocumentKeyCRUD(db_session).create_item(
            {
                "document_id": document.id,
                "file_id": file.id,
                "name": self.BASELINE_KEY,
                "value": "100",
                "status": "accepted",
            }
        )

        response = client.put(
            self._key_endpoint(site_id, document.id),
            headers=company_member_user_auth_header,
            json={"name": self.BASELINE_KEY, "value": "999", "file_id": file.id},
        )

        assert response.status_code == 422
        assert "override_notes" in response.json()["message"]
        # The previously stored value is untouched by the rejected change.
        saved = DocumentKeyCRUD(db_session).get_document_key(
            name=self.BASELINE_KEY, document_id=document.id, file_id=file.id
        )
        assert saved.value == "100"
        assert saved.status == "accepted"

    def test_reaccept_clears_existing_key_override_columns(
        self, client, site_id, document, file, db_session, company_member_user_auth_header, non_system_user_id, monkeypatch
    ):
        """Re-accepting a previously-overridden key (value back to the AI original) clears override columns."""
        self._patch_allowed_keys(monkeypatch, [self.BASELINE_KEY])
        field = self._make_canonical_field(db_session, self.CANONICAL_NAME, self.BASELINE_KEY)
        self._make_candidate_fact(db_session, document.site_id, field.id, file.id, "100", "100")
        DocumentKeyCRUD(db_session).create_item(
            {
                "document_id": document.id,
                "file_id": file.id,
                "name": self.BASELINE_KEY,
                "value": "100",
                "status": "overridden",
                "override_value": "999",
                "overridden_by_id": non_system_user_id,
                "overridden_at": datetime.now(timezone.utc),
                "override_notes": "prior override rationale",
            }
        )

        response = client.put(
            self._key_endpoint(site_id, document.id),
            headers=company_member_user_auth_header,
            json={"name": self.BASELINE_KEY, "value": "100", "file_id": file.id},
        )

        assert response.status_code == 202
        saved = DocumentKeyCRUD(db_session).get_document_key(
            name=self.BASELINE_KEY, document_id=document.id, file_id=file.id
        )
        assert saved.status == "accepted"
        assert saved.override_value is None
        assert saved.overridden_by_id is None
        assert saved.overridden_at is None
        assert saved.override_notes is None


class TestSetKeyDoesNotWriteBigQuery:
    """DD V2 Phase 5B — the legacy DD -> BigQuery characteristics write was removed.

    Accepting/overriding a Due Diligence key (including the As-built PV Syst keys that
    previously triggered the BigQuery upsert) must succeed WITHOUT any BigQuery I/O. Reviewed
    values now flow only into ``project_facts``; DD review/promotion no longer depends on
    BigQuery being reachable.
    """

    BASELINE_KEY = "Module Wattage"
    CANONICAL_NAME = "module_wattage"
    # Patch the shared base method so ANY characteristics-handler subclass write is caught.
    SYNC_TARGET = "app.helpers.bq_data_sync_helper.CharacteristicsHandler.sync_to_bq"

    @staticmethod
    def _key_endpoint(site_id_, document_id_):
        return f"/api/due-diligence/{site_id_}/documents/{document_id_}/keys"

    @staticmethod
    def _patch_allowed_keys(monkeypatch, allowed):
        # Registry is not seeded in the test DB and config fallback is off, so the
        # allowed-keys set must be supplied explicitly (mirrors the guardrail tests).
        monkeypatch.setattr(
            "app.routers.due_diligence.documents.AIParsingHandler.get_keys_by_document_type",
            lambda self, document_type: list(allowed),
        )

    @classmethod
    def _spy_sync_to_bq(cls, monkeypatch):
        """Record any BigQuery characteristics write; the DD path must never trigger one."""
        calls = []

        def _record(self, old_record, new_record):
            calls.append((old_record, new_record))
            return True

        monkeypatch.setattr(cls.SYNC_TARGET, _record)
        return calls

    @classmethod
    def _ensure_canonical_field(cls, db_session):
        # canonical_fields.name is UNIQUE and the session is shared, so get-or-create.
        field = db_session.query(CanonicalField).filter_by(name=cls.CANONICAL_NAME).first()
        if field is None:
            field = CanonicalField(
                name=cls.CANONICAL_NAME, display_name=cls.BASELINE_KEY, field_type="text", is_active=True
            )
            db_session.add(field)
            db_session.commit()
            db_session.refresh(field)
        return field

    def test_baseline_key_update_does_not_write_to_bigquery(
        self, client, site_id, document, file, db_session, company_member_user_auth_header, monkeypatch
    ):
        """A former-BQ key ('Module Wattage') update + rationale -> 202 and zero BigQuery writes."""
        self._patch_allowed_keys(monkeypatch, [self.BASELINE_KEY])
        self._ensure_canonical_field(db_session)
        calls = self._spy_sync_to_bq(monkeypatch)

        response = client.put(
            self._key_endpoint(site_id, document.id),
            headers=company_member_user_auth_header,
            json={
                "name": self.BASELINE_KEY,
                "value": "987654",
                "file_id": file.id,
                # Always pass a rationale so the result is 202 regardless of any AI original.
                "override_notes": "DD V2 Phase 5B no-BigQuery regression guard",
            },
        )

        assert response.status_code == 202
        assert calls == []  # legacy DD -> BigQuery sync was removed; nothing should be written

    def test_non_baseline_key_accept_does_not_write_to_bigquery(
        self, client, site_id, document, file, company_member_user_auth_header, monkeypatch
    ):
        """A plain DD key accept succeeds with no BigQuery mocks present and triggers no write."""
        self._patch_allowed_keys(monkeypatch, ["Quiet Enjoyment"])
        calls = self._spy_sync_to_bq(monkeypatch)

        response = client.put(
            self._key_endpoint(site_id, document.id),
            headers=company_member_user_auth_header,
            json={"name": "Quiet Enjoyment", "value": "Materially changed text", "file_id": file.id},
        )

        assert response.status_code == 202
        assert calls == []

    def test_documents_router_has_no_bigquery_path(self):
        """Static guard: the documents router contains no BigQuery sync code path."""
        import inspect

        import app.routers.due_diligence.documents as documents_module

        source = inspect.getsource(documents_module)
        # Assert the concrete BigQuery code symbols are gone. (The word "BigQuery" may
        # still appear in an explanatory Phase-5B comment, so we check identifiers, not prose.)
        for forbidden in (
            "SiteDDCharacteristicsHandler",
            "prepare_keys_sync_payload",
            "sync_to_bq",
            "DueDiligenceBQKeys",
            "document_key_sync_helper",
        ):
            assert forbidden not in source, f"unexpected reference to {forbidden} in documents router"

import copy
import logging
from copy import deepcopy
from datetime import datetime, timezone

import pytest

import tests.unit.samples as samples
from app.crud.company import CompanyCRUD
from app.crud.document_key import DocumentKeyCRUD
from app.crud.site import SiteCRUD
from app.crud.site_additional_fields_list import SiteAdditionalFieldListCRUD
from app.static.default_site_documents_enum import SiteDocumentsEnum
from app.static.sites import SiteDetailsSections
from tests.fixtures.sites import create_default_site_document_sections_for_test, generate_default_site_documents_for_test
from tests.utils import get_document_by_name


class TestAssetManagementSites:
    """Tests for sites routes."""

    @staticmethod
    def _generate_list_endpoint():
        """/api/sites"""
        return "/api/sites"

    def _generate_individual_endpoint(self, site_id_):
        """/api/sites/{site_id}"""
        return f"{self._generate_list_endpoint()}/{site_id_}"

    def _generate_details_endpoint(self, site_id_):
        """/api/sites/{site_id}/details"""
        return f"{self._generate_individual_endpoint(site_id_)}/details"

    def _generate_affected_devices_endpoint(self, site_id_):
        """/api/sites/{site_id}/affected-devices"""
        return f"{self._generate_individual_endpoint(site_id_)}/affected-devices"

    def test_site_creation_success(self, client, company_id, system_user_auth_header, caplog, monkeypatch):
        """Test that with valid body site will be created and endpoint returns 201 Created status code."""
        # monkey patch methods for site default documents creation to not create all 300+ documents
        monkeypatch.setattr(
            "app.routers.assets_management.sites.create_default_site_document_sections",
            create_default_site_document_sections_for_test,
        )
        monkeypatch.setattr(
            "app.routers.assets_management.sites.generate_default_site_documents",
            generate_default_site_documents_for_test,
        )
        caplog.set_level(logging.INFO)
        payload = copy.deepcopy(samples.VALID_SITE_BODY1)
        payload["company_id"] = company_id
        response = client.post(self._generate_list_endpoint(), json=payload, headers=system_user_auth_header)

        # check if board helper was executed by validating it log message
        board_helper_completion_log = False
        for log in caplog.records:
            if "Created 5 default statuses for site board with id=" in log.message:
                board_helper_completion_log = True

        assert response.status_code == 201
        assert response.json()["message"] == "Site has been created"
        assert board_helper_completion_log

    def test_site_creation_company_admin(
        self, client, company_id, company_member_user_auth_header, company_member_user, caplog, monkeypatch, db_session
    ):
        """Test that with valid body site will be created by company admin,
        and it will be attached to company admin project access."""
        # monkey patch methods for site default documents creation to not create all 300+ documents
        monkeypatch.setattr(
            "app.routers.assets_management.sites.create_default_site_document_sections",
            create_default_site_document_sections_for_test,
        )
        monkeypatch.setattr(
            "app.routers.assets_management.sites.generate_default_site_documents",
            generate_default_site_documents_for_test,
        )
        # Validate user has only one default site in project access
        assert len(company_member_user.sites) == 1
        caplog.set_level(logging.INFO)
        payload = copy.deepcopy(samples.VALID_SITE_BODY1)
        payload["company_id"] = company_id
        response = client.post(self._generate_list_endpoint(), json=payload, headers=company_member_user_auth_header)

        assert response.status_code == 201
        assert response.json()["message"] == "Site has been created"
        # validate company admin got site access
        db_session.refresh(company_member_user)
        assert len(company_member_user.sites) == 2

    def test_site_creation_company_admin_no_access(
        self, client, company_id, company_member_user_auth_header, company_member_user, caplog, monkeypatch, db_session
    ):
        """Test that with valid body site can not be created for company where user has no rights."""
        # monkey patch methods for site default documents creation to not create all 300+ documents
        monkeypatch.setattr(
            "app.routers.assets_management.sites.create_default_site_document_sections",
            create_default_site_document_sections_for_test,
        )
        monkeypatch.setattr(
            "app.routers.assets_management.sites.generate_default_site_documents",
            generate_default_site_documents_for_test,
        )
        # Validate user has only one default site in project access
        assert len(company_member_user.sites) == 1
        caplog.set_level(logging.INFO)
        # create new company and try to create a new site for this company
        company_crud = CompanyCRUD(db_session)
        new_company = company_crud.create_item({"name": "new_company", "company_type": "project_site_owner"})
        payload = copy.deepcopy(samples.VALID_SITE_BODY1)
        payload["company_id"] = new_company.id
        response = client.post(self._generate_list_endpoint(), json=payload, headers=company_member_user_auth_header)

        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"
        company_crud.delete_by_id(new_company.id)

    @pytest.mark.parametrize(
        ("target_field_name", "invalid_value", "expected_msg"),
        (
            ("zip_code", "123sd1", samples.INVALID_SITE_ZIP_CODE_MSG),
            ("zip_code", "123456", samples.INVALID_SITE_ZIP_CODE_TO_LONG_MSG),
        ),
    )
    def test_site_creation_with_invalid_body(
        self, client, company_id, system_user_auth_header, target_field_name, invalid_value, expected_msg
    ):
        """Test that with invalid body (missing essential field) the site won't be created and endpoint returns
        422 Unprocessable entity.
        """
        invalid_body = deepcopy(samples.VALID_SITE_BODY1)
        invalid_body["company_id"] = company_id
        invalid_body[target_field_name] = invalid_value

        response = client.post(self._generate_list_endpoint(), json=invalid_body, headers=system_user_auth_header)

        assert response.status_code == 422
        assert response.json()["message"] == expected_msg

    @pytest.mark.parametrize("sites", [3], indirect=True)
    def test_get_sites_no_filter(
        self, client, db_session, company_id, system_user_auth_header, sites, all_site_documents
    ):
        """Test get all sites without filters order by id.

        Use System user to get all sites"""

        response = client.get(self._generate_list_endpoint(), params={"order_by": "id"}, headers=system_user_auth_header)
        response_json = response.json()
        sorted_items = sorted(response_json["items"], key=lambda d: d["id"])

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 10

        items = response_json["items"]

        assert items[0]["id"] == sorted_items[0]["id"]
        assert items[1]["id"] == sorted_items[1]["id"]

    def test_get_sites_with_extra_sources(
        self, client, db_session, company_member_user_auth_header, site, all_site_documents
    ):
        """Test values from <site_additional_fields> table and due diligence documents are picked up correctly"""

        # add values for the site extras
        site_details_crud = SiteAdditionalFieldListCRUD(db_session)
        site_details_fields = {
            "status": "sold",
            "das_provider": "DAS",
            "ownership_structure": "Cooperation",
            "placed_in_service_date": "2024-12-21",
        }
        site_details_crud.create_item({"site_id": site.id, **site_details_fields})

        # status is enum field, update expected response accordingly
        expected_site_details_fields = copy.deepcopy(site_details_fields)
        expected_site_details_fields["status"] = "Sold"

        # prepare due diligence related keys by passing it to the corresponding DD documents
        expected_due_diligence_fields = {
            "production_guarantee": "Test Production Guarantee",
            "o_and_m_provider": "Test O&M Provider",
            "utility_provider": "Test Utility Provider",
            "epc_provider": "Test EPC Provider",
        }
        onm_doc = get_document_by_name(site.documents, SiteDocumentsEnum.om_agreement)
        iaa_doc = get_document_by_name(site.documents, SiteDocumentsEnum.interconnection_agreement_and_amendments)
        epc_doc = get_document_by_name(site.documents, SiteDocumentsEnum.epc_agreement)
        key_items_to_be_added = [
            {
                "document_id": onm_doc.id,
                "name": "Production Guarantee",
                "value": expected_due_diligence_fields["production_guarantee"],
            },
            {
                "document_id": onm_doc.id,
                "name": "Provider",
                "value": expected_due_diligence_fields["o_and_m_provider"],
            },
            {
                "document_id": iaa_doc.id,
                "name": "Interconnection Utility Company",
                "value": expected_due_diligence_fields["utility_provider"],
            },
            {
                "document_id": epc_doc.id,
                "name": "EPC Contractor Name",
                "value": expected_due_diligence_fields["epc_provider"],
            },
        ]
        document_keys_crud = DocumentKeyCRUD(db_session)
        document_keys_crud.create_items(key_items_to_be_added)

        # prepare expected response object with generic company details, site additional fields and the DD details
        expected_company_payload = copy.deepcopy(samples.TEST_COMPANY_PAYLOAD_JSON)
        expected_company_payload["id"] = site.company_id
        expected_site_response = {
            **samples.TEST_SITE_BODY_JSON_WITHOUT_CAMERA_DETAILS,
            **expected_site_details_fields,
            **expected_due_diligence_fields,
            "id": site.id,
            "company": expected_company_payload,
        }

        response = client.get(self._generate_list_endpoint(), headers=company_member_user_auth_header)
        response_site = response.json()["items"][0]

        assert response.status_code == 200
        assert response_site == expected_site_response

    def test_get_sites_w_system_sizes_floats(
        self, client, db_session, company_id, company_member_user_auth_header, site, all_site_documents
    ):
        """Ensure that site system sizes are rounded to 2 decimal places.

        Tests the bug https://softserve-jirasw.atlassian.net/browse/IOSP1-820
        """
        site.system_size_ac = 10.97432101423413
        site.system_size_dc = 7.0515154151
        db_session.commit()

        response = client.get(
            self._generate_list_endpoint(), params={"company_id": company_id}, headers=company_member_user_auth_header
        )
        response_json = response.json()
        assert response.status_code == 200

        retrieved_site = response_json["items"][0]
        assert retrieved_site["id"] == site.id

        # ensure that new site system size is rounded and limited to 2 digits scale:
        assert retrieved_site["system_size_ac"] == 10.97
        assert retrieved_site["system_size_dc"] == 7.05

    def test_get_sites_no_existing_company(self, client, company_member_user_auth_header, site_id):
        """Test get all sites with filter to get for non-existing company."""
        response = client.get(
            self._generate_list_endpoint(), params={"company_id": "11111111"}, headers=company_member_user_auth_header
        )
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 10

        assert len(response_json["items"]) == 0

    def test_get_sites_invalid_filters(self, client, system_user_auth_header):
        """Test that with invalid filter value endpoint returns 422 Validation error."""
        response = client.get(
            self._generate_list_endpoint(), params={"state": "incorrect state"}, headers=system_user_auth_header
        )

        assert response.status_code == 422
        assert response.json()["message"] == samples.INVALID_STATE_FILTER_MSG

    def test_get_sites_by_specified_filter(self, client, company_member_user_auth_header, site_id, all_site_documents):
        """Test get all sites with given filter."""
        response = client.get(
            self._generate_list_endpoint(), params={"state": "ME"}, headers=company_member_user_auth_header
        )

        response_json = response.json()

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 10
        assert len(response_json["items"]) == 1

        site = response_json["items"][0]
        assert site["name"] == samples.TEST_SITE_NAME
        assert site["state"] == "ME"

    def test_get_sites_search_by_name(self, client, company_member_user_auth_header, site_id, all_site_documents):
        """Test get all sites search by site name."""
        response = client.get(
            self._generate_list_endpoint(),
            params={"search": samples.TEST_SITE_NAME},
            headers=company_member_user_auth_header,
        )
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 10

        assert len(response_json["items"]) == 1
        assert response_json["items"][0]["name"] == samples.TEST_SITE_NAME

    def test_get_by_system_user_sites(self, client, site, system_user_auth_header, all_site_documents):
        """Test sites GET by system user receive all sites."""
        response = client.get(self._generate_list_endpoint(), headers=system_user_auth_header)
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 10

        assert len(response_json["items"]) == 1

    def test_get_site_by_id(self, client, company_member_user_auth_header, site_id, company_id):
        """Test that site fetch by id returns appropriate values as expected."""
        # build full site body considering dynamic fields
        expected_response = deepcopy(samples.TEST_SITE_BODY_JSON)
        expected_response["id"] = site_id
        expected_response.update(samples.TEST_SITE_DAS_CONNECTION_FIELDS)
        company = deepcopy(samples.TEST_COMPANY_PAYLOAD_JSON)
        company["id"] = company_id
        expected_response["company"] = company

        response = client.get(self._generate_individual_endpoint(site_id), headers=company_member_user_auth_header)
        response_json = response.json()

        assert response.status_code == 200
        assert response_json == expected_response

    def test_get_site_by_id_w_system_size_floats(self, client, system_user_auth_header, company_id, db_session):
        """Ensure that site system sizes are rounded to 2 decimal places.

        Tests the bug https://softserve-jirasw.atlassian.net/browse/IOSP1-820
        """
        payload = deepcopy(samples.TEST_SITE_BODY)
        payload.update({"company_id": company_id, "system_size_ac": 10.34432101423413, "system_size_dc": 7.545151545151})
        sites_crud = SiteCRUD(db_session)
        test_site_id = sites_crud.create_item(payload).id

        response = client.get(self._generate_individual_endpoint(test_site_id), headers=system_user_auth_header)
        response_json = response.json()

        assert response.status_code == 200
        # ensure that new site system size is rounded and limited to 2 digits scale:
        assert response_json["system_size_ac"] == 10.34
        assert response_json["system_size_dc"] == 7.55

        # teardown
        sites_crud.delete_by_id(test_site_id)

    def test_get_site_by_id_not_exists(self, client, system_user_auth_header):
        """Test that site fetch by id returns 404 if site not exists."""
        target_id = 123456789
        response = client.get(self._generate_individual_endpoint(target_id), headers=system_user_auth_header)

        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_get_site_details(
        self, client, company_member_user_auth_header, site_id, all_site_documents, ppa_agreement_ai_fields
    ):
        """Test that site details fetch by id returns appropriate values as expected."""

        response = client.get(self._generate_details_endpoint(site_id), headers=company_member_user_auth_header)

        assert response.status_code == 200
        assert response.json() == samples.TEST_SITE_DETAILS_BODY_JSON

    @pytest.mark.parametrize(
        "year_now, month_now, expected_remaining_ppa_term",
        (
            (2015, 12, "20 years, 0 months"),  # ppa term not started yet
            (2022, 12, "20 years, 0 months"),
            (2023, 1, "19 years, 11 months"),
            (2023, 11, "19 years, 1 month"),
            (2023, 12, "19 years, 0 months"),
        ),
    )
    def test_get_site_details_w_remaining_ppa_term(
        self,
        client,
        company_member_user_auth_header,
        site_id,
        freezer,
        year_now,
        month_now,
        expected_remaining_ppa_term,
        db_session,
        all_site_documents,
        ppa_agreement_ai_fields,
    ):
        """Test that computed field remaining_ppa_term is calculated appropriately regarding ppa_term duration,
        ppa term start date and the provided frozen by the test the date now.

        In case the ppa term has not started yet: ppa_remaining_term should be equal to ppa_term but neatly formatted
        in the same style.
        """
        freezer.move_to(datetime(year_now, month_now, day=1, tzinfo=timezone.utc))
        response = client.get(self._generate_details_endpoint(site_id), headers=company_member_user_auth_header)

        assert response.status_code == 200
        response_json = response.json()

        assert response_json["interconnection"]["remaining_ppa_term"] == expected_remaining_ppa_term

    @pytest.mark.freeze_time("2050-12-01")
    def test_get_site_details_w_remaining_ppa_term_expired(
        self, client, company_member_user_auth_header, site_id, all_site_documents, ppa_agreement_ai_fields
    ):
        """Test that in case of expired ppa_term the remaining_ppa_term is represented as a str with 0 years, 0 months
        without negative numbers.

        It is a separate test to have ability to use pytest.mark.freeze_time to bypass datetime.now inconsistency when
        company_member_user_auth_header fixture generates a different time auth token.
        """
        response = client.get(self._generate_details_endpoint(site_id), headers=company_member_user_auth_header)

        assert response.status_code == 200
        assert response.json()["interconnection"]["remaining_ppa_term"] == "0 years, 0 months"

    @pytest.mark.freeze_time("2041-11-01")
    def test_get_site_details_w_remaining_ppa_term_singular(
        self, client, company_member_user_auth_header, site_id, all_site_documents, ppa_agreement_ai_fields
    ):
        """Test that ppa_remaining_term str is formatted appropriately with singular 'year' and 'month' in case there
        are indeed only one year and month.

        It is a separate test to have ability to use pytest.mark.freeze_time to bypass datetime.now inconsistency when
        company_member_user_auth_header fixture generates a different time auth token.
        """
        response = client.get(self._generate_details_endpoint(site_id), headers=company_member_user_auth_header)

        assert response.status_code == 200
        assert response.json()["interconnection"]["remaining_ppa_term"] == "1 year, 1 month"

    def test_get_site_details_but_id_not_exists(self, client, system_user_auth_header):
        """Test that site details fetch by id returns 404 if site not exists."""
        target_id = 123456789
        response = client.get(self._generate_details_endpoint(target_id), headers=system_user_auth_header)

        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_update_site(self, client, company_member_user_auth_header, site_id):
        """Test update site fields."""
        updated_site = deepcopy(samples.TEST_SITE_BODY_JSON)
        updated_site["name"] = "New site name"
        response = client.put(
            self._generate_individual_endpoint(site_id), json=updated_site, headers=company_member_user_auth_header
        )

        assert response.status_code == 202
        assert response.json()["message"] == "Site has been updated"

    def test_update_site_not_found(self, client, system_user_auth_header):
        """Test update site for non-existent ID."""
        target_id = 123243454365465647
        response = client.put(
            self._generate_individual_endpoint(target_id),
            json=samples.TEST_SITE_BODY_JSON,
            headers=system_user_auth_header,
        )

        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_update_site_403(self, client, site_id, company_member_user_auth_header):
        """Test update site that does not belong to user company."""

        not_admin_site = site_id + 1
        response = client.put(
            self._generate_individual_endpoint(not_admin_site),
            json=samples.TEST_SITE_BODY_JSON,
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_get_site_by_id_w_403_authz(self, client, non_system_user_auth_header, site_id):
        """Test that sites GET endpoint detects non-system user without needed permissions and throws 403."""

        response = client.get(self._generate_individual_endpoint(site_id), headers=non_system_user_auth_header)
        assert response.status_code == 403

    def test_get_potential_affected_devices(
        self,
        client,
        company_member_user_auth_header,
        company_id,
        site_id,
        device,
    ):
        """Test that get potential task affected devices receives list of devices related to a site."""
        response = client.get(self._generate_affected_devices_endpoint(site_id), headers=company_member_user_auth_header)
        response_json = response.json()["items"][0]

        assert response.status_code == 200
        assert response_json["id"] == device.id
        assert response_json["name"] == device.name

    def test_get_potential_affected_devices_search(
        self,
        client,
        company_member_user_auth_header,
        company_id,
        site_id,
        device,
    ):
        """Test that get potential task affected devices receives list of devices related to a site."""
        response = client.get(
            self._generate_affected_devices_endpoint(site_id),
            headers=company_member_user_auth_header,
            params={"search": device.name},
        )
        response_json = response.json()["items"][0]

        assert response.status_code == 200
        assert response_json["id"] == device.id
        assert response_json["name"] == device.name

        response_no_devices = client.get(
            self._generate_affected_devices_endpoint(site_id),
            headers=company_member_user_auth_header,
            params={"search": "random_name"},
        )
        assert response.status_code == 200
        assert len(response_no_devices.json()["items"]) == 0

    def test_get_potential_affected_devices_403(self, client, non_system_user_auth_header, site_id):
        """Test that get potential task affected devices receives 403."""
        response = client.get(self._generate_affected_devices_endpoint(site_id), headers=non_system_user_auth_header)
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_get_potential_affected_devices_404(self, client, company_member_user_auth_header, site_id):
        """Test that get potential task affected devices receives 404."""
        response = client.get(self._generate_affected_devices_endpoint(12345), headers=company_member_user_auth_header)
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    @pytest.mark.parametrize(
        "section_name,section_payload,expected_updated_section",
        (
            (
                SiteDetailsSections.site_level_details.value,
                samples.TEST_SITE_DETAILS_SITE_LEVEL_SECTION_UPDATE_PAYLOAD,
                samples.TEST_SITE_DETAILS_SITE_LEVEL_SECTION_UPDATED,
            ),
            (
                SiteDetailsSections.asset_overview.value,
                samples.TEST_SITE_DETAILS_ASSET_OVERVIEW_SECTION_UPDATE_PAYLOAD,
                samples.TEST_SITE_DETAILS_ASSET_OVERVIEW_SECTION_UPDATED,
            ),
            (
                SiteDetailsSections.ownership.value,
                samples.TEST_SITE_DETAILS_OWNERSHIP_SECTION_UPDATE_PAYLOAD,
                samples.TEST_SITE_DETAILS_OWNERSHIP_SECTION_UPDATED,
            ),
            (
                SiteDetailsSections.tax_equity.value,
                samples.TEST_SITE_DETAILS_TAX_EQUITY_SECTION_UPDATE_PAYLOAD,
                samples.TEST_SITE_DETAILS_TAX_EQUITY_SECTION_UPDATED,
            ),
            (
                SiteDetailsSections.key_dates.value,
                samples.TEST_SITE_DETAILS_KEY_DATES_SECTION_UPDATE_PAYLOAD,
                samples.TEST_SITE_DETAILS_KEY_DATES_SECTION_SECTION_UPDATED,
            ),
            (
                SiteDetailsSections.o_and_m.value,
                samples.TEST_SITE_DETAILS_OM_SECTION_UPDATE_PAYLOAD,
                samples.TEST_SITE_DETAILS_OM_SECTION_UPDATED,
            ),
            (
                SiteDetailsSections.interconnection.value,
                samples.TEST_SITE_DETAILS_INTERCONNECTION_SECTION_UPDATE_PAYLOAD,
                samples.TEST_SITE_DETAILS_INTERCONNECTION_SECTION_UPDATED,
            ),
            (
                SiteDetailsSections.epc_contractor.value,
                samples.TEST_SITE_DETAILS_EPC_CONTRACTOR_SECTION_UPDATE_PAYLOAD,
                samples.TEST_SITE_DETAILS_EPC_CONTRACTOR_SECTION_UPDATED,
            ),
            (
                SiteDetailsSections.community_solar_manager.value,
                samples.TEST_SITE_DETAILS_CSM_SECTION_UPDATE_PAYLOAD,
                samples.TEST_SITE_DETAILS_CSM_SECTION_UPDATED,
            ),
            (
                SiteDetailsSections.insurance_provider.value,
                samples.TEST_SITE_DETAILS_INSURANCE_PROVIDER_SECTION_UPDATE_PAYLOAD,
                samples.TEST_SITE_DETAILS_INSURANCE_PROVIDER_SECTION_UPDATED,
            ),
            (
                SiteDetailsSections.site_lease.value,
                samples.TEST_SITE_DETAILS_SITE_LEASE_SECTION_UPDATE_PAYLOAD,
                samples.TEST_SITE_DETAILS_SITE_LEASE_SECTION_UPDATED,
            ),
            (
                SiteDetailsSections.vegetation_vendor.value,
                samples.TEST_SITE_DETAILS_VEGETATION_VENDOR_SECTION_UPDATE_PAYLOAD,
                samples.TEST_SITE_DETAILS_VEGETATION_VENDOR_SECTION_UPDATED,
            ),
            (
                SiteDetailsSections.offtaker.value,
                samples.TEST_SITE_DETAILS_OFFTAKER_SECTION_UPDATE_PAYLOAD,
                samples.TEST_SITE_DETAILS_OFFTAKER_SECTION_UPDATED,
            ),
            (
                SiteDetailsSections.compliance.value,
                samples.TEST_SITE_DETAILS_COMPLIANCE_SECTION_UPDATE_PAYLOAD,
                samples.TEST_SITE_DETAILS_COMPLIANCE_SECTION_UPDATED,
            ),
        ),
    )
    def test_update_site_details_success(
        self,
        client,
        company_member_user_auth_header,
        site_id,
        all_site_documents,
        section_name,
        section_payload,
        expected_updated_section,
        ignore_bq_sync,
    ):
        """Validates site details per-section update, happy path"""

        put_response = client.put(
            self._generate_details_endpoint(site_id),
            headers=company_member_user_auth_header,
            params={"section_name": section_name},
            json=section_payload,
        )
        get_response = client.get(self._generate_details_endpoint(site_id), headers=company_member_user_auth_header)

        assert put_response.status_code == 202
        assert get_response.status_code == 200
        assert get_response.json()[section_name] == expected_updated_section

    @pytest.mark.parametrize(
        "section_name,section_payload,expected_error_message",
        (
            (
                SiteDetailsSections.site_level_details.value,
                samples.TEST_SITE_DETAILS_SITE_LEVEL_SECTION_UPDATE_PAYLOAD_INVALID,
                samples.TEST_SITE_DETAILS_SITE_LEVEL_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR,
            ),
            (
                SiteDetailsSections.asset_overview.value,
                samples.TEST_SITE_DETAILS_ASSET_OVERVIEW_SECTION_UPDATE_PAYLOAD_INVALID,
                samples.TEST_SITE_DETAILS_ASSET_OVERVIEW_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR,
            ),
            (
                SiteDetailsSections.ownership.value,
                samples.TEST_SITE_DETAILS_OWNERSHIP_SECTION_UPDATE_PAYLOAD_INVALID,
                samples.TEST_SITE_DETAILS_OWNERSHIP_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR,
            ),
            (
                SiteDetailsSections.tax_equity.value,
                samples.TEST_SITE_DETAILS_TAX_EQUITY_SECTION_UPDATE_PAYLOAD_INVALID,
                samples.TEST_SITE_DETAILS_TAX_EQUITY_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR,
            ),
            (
                SiteDetailsSections.key_dates.value,
                samples.TEST_SITE_DETAILS_KEY_DATES_SECTION_UPDATE_PAYLOAD_INVALID,
                samples.TEST_SITE_DETAILS_KEY_DATES_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR,
            ),
            # validate required fields are validates
            (
                SiteDetailsSections.o_and_m.value,
                samples.TEST_SITE_DETAILS_OM_SECTION_UPDATE_PAYLOAD_INVALID,
                samples.TEST_SITE_DETAILS_OM_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR,
            ),
            (
                SiteDetailsSections.interconnection.value,
                samples.TEST_SITE_DETAILS_INTERCONNECTION_SECTION_UPDATE_PAYLOAD_INVALID,
                samples.TEST_SITE_DETAILS_INTERCONNECTION_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR,
            ),
            (
                SiteDetailsSections.epc_contractor.value,
                samples.TEST_SITE_DETAILS_EPC_CONTRACTOR_SECTION_UPDATE_PAYLOAD_INVALID,
                samples.TEST_SITE_DETAILS_EPC_CONTRACTOR_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR,
            ),
            (
                SiteDetailsSections.community_solar_manager.value,
                samples.TEST_SITE_DETAILS_CSM_SECTION_UPDATE_PAYLOAD_INVALID,
                samples.TEST_SITE_DETAILS_CSM_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR,
            ),
            (
                SiteDetailsSections.insurance_provider.value,
                samples.TEST_SITE_DETAILS_INSURANCE_PROVIDER_SECTION_UPDATE_PAYLOAD_INVALID,
                samples.TEST_SITE_DETAILS_INSURANCE_PROVIDER_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR,
            ),
            (
                SiteDetailsSections.site_lease.value,
                samples.TEST_SITE_DETAILS_SITE_LEASE_SECTION_UPDATE_PAYLOAD_INVALID,
                samples.TEST_SITE_DETAILS_SITE_LEASE_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR,
            ),
            (
                SiteDetailsSections.vegetation_vendor.value,
                samples.TEST_SITE_DETAILS_VEGETATION_VENDOR_SECTION_UPDATE_PAYLOAD_INVALID,
                samples.TEST_SITE_DETAILS_VEGETATION_VENDOR_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR,
            ),
            (
                SiteDetailsSections.offtaker.value,
                samples.TEST_SITE_DETAILS_OFFTAKER_SECTION_UPDATE_PAYLOAD_INVALID,
                samples.TEST_SITE_DETAILS_OFFTAKER_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR,
            ),
            (
                SiteDetailsSections.compliance.value,
                samples.TEST_SITE_DETAILS_COMPLIANCE_SECTION_UPDATE_PAYLOAD_INVALID,
                samples.TEST_SITE_DETAILS_COMPLIANCE_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR,
            ),
            # special cases for date validation, validate cases of IOSP1-3446
            (
                SiteDetailsSections.tax_equity.value,
                samples.TEST_SITE_DETAILS_TAX_EQUITY_SECTION_UPDATE_PAYLOAD_INVALID_DATES,
                samples.TEST_SITE_DETAILS_TAX_EQUITY_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR_DATES,
            ),
            (
                SiteDetailsSections.community_solar_manager.value,
                samples.TEST_SITE_DETAILS_CSM_SECTION_UPDATE_PAYLOAD_INVALID_DATES,
                samples.TEST_SITE_DETAILS_CSM_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR_DATES,
            ),
            (
                SiteDetailsSections.compliance.value,
                samples.TEST_SITE_DETAILS_COMPLIANCE_SECTION_UPDATE_PAYLOAD_INVALID_DATES,
                samples.TEST_SITE_DETAILS_COMPLIANCE_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR_DATES,
            ),
            (
                SiteDetailsSections.key_dates.value,
                samples.TEST_SITE_DETAILS_KEY_DATES_SECTION_UPDATE_PAYLOAD_INVALID_DATES,
                samples.TEST_SITE_DETAILS_KEY_DATES_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR_DATES,
            ),
            (
                SiteDetailsSections.offtaker.value,
                samples.TEST_SITE_DETAILS_OFFTAKER_SECTION_UPDATE_PAYLOAD_INVALID_DATES,
                samples.TEST_SITE_DETAILS_OFFTAKER_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR_DATES,
            ),
        ),
    )
    def test_update_site_details_validation_error(
        self,
        client,
        company_member_user_auth_header,
        site_id,
        all_site_documents,
        section_name,
        section_payload,
        expected_error_message,
    ):
        """Validates site details per-section update, ensure requested validation was applied"""

        response = client.put(
            self._generate_details_endpoint(site_id),
            headers=company_member_user_auth_header,
            params={"section_name": section_name},
            json=section_payload,
        )
        assert response.status_code == 422
        assert response.json()["message"] == expected_error_message

    def test_update_site_details_query_param_error(
        self,
        client,
        company_member_user_auth_header,
        site_id,
    ):
        """Validates API handled only pre-defined sections updates"""

        response = client.put(
            self._generate_details_endpoint(site_id),
            headers=company_member_user_auth_header,
            params={"section_name": "invalid_section_name"},
            json={"test": "test"},
        )
        assert response.status_code == 400
        assert response.json()["message"] == samples.SITE_DETAILS_UPDATE_INVALID_SECTION_NAME_ERROR

    @pytest.mark.parametrize(
        "om_rating_value",
        (
            # bug number can be set
            9999999999999,
            # decimal is set and not rounded
            4.25,
        ),
    )
    def test_site_details_values_set_correctly(
        self, client, company_member_user_auth_header, site_id, om_rating_value, all_site_documents
    ):
        """Validation for IOSP1-3562, ensure O&M rating is set exactly by the input data"""
        client.put(
            self._generate_details_endpoint(site_id),
            headers=company_member_user_auth_header,
            params={"section_name": SiteDetailsSections.o_and_m.value},
            json={"o_and_m_rate": om_rating_value},
        )

        response = client.get(
            self._generate_details_endpoint(site_id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json()["o_and_m"]["o_and_m_rate"] == om_rating_value

"""Tests for companies routes."""

import copy
from copy import deepcopy

import pytest

import tests.unit.samples as samples
from tests.utils import clean_up_companies, remove_dynamic_fields


class TestContractors:
    """Tests for contractors routes."""

    COMPANIES_API_ENDPOINT = "/api/companies"
    CONTRACTORS_API_ENDPOINT = "/api/contractors"
    SITES_API_ENDPOINT = "/api/sites"
    USERS_API_ENDPOINT = "/api/users"

    def test_contractor_creation_success(self, client, system_user_auth_header):
        response = client.post(
            self.CONTRACTORS_API_ENDPOINT, json=samples.VALID_CONTRACTOR_BODY, headers=system_user_auth_header
        )

        assert response.status_code == 201
        assert response.json() == {"code": 201, "message": "Company has been successfully created"}

    def test_contractor_creation_w_invalid_body(self, client, system_user_auth_header):
        """Test that with invalid body (missing essential field) the company won't be created and endpoint returns
        422 Unprocessable entity.
        """
        invalid_body = deepcopy(samples.VALID_CONTRACTOR_BODY)
        del invalid_body["company_type"]

        response = client.post(self.CONTRACTORS_API_ENDPOINT, json=invalid_body, headers=system_user_auth_header)
        assert response.status_code == 422
        assert response.json() == {"code": 422, "message": "Validation error: body.company_type - Field required"}

    @pytest.mark.parametrize(
        ("target_field_name", "invalid_value", "expected_status_code", "expected_msg"),
        (
            ("email", "hello@gmail.com@yahoo.com", 422, samples.BODY_EMAIL_PATTERN_MISMATCH_ERR),
            ("email", "hellogmail.com", 422, samples.BODY_EMAIL_PATTERN_MISMATCH_ERR),
            ("email", samples.LONGER_THAN_100_CHARS_EMAIL, 422, samples.EMAIL_LENGTH_ERROR),
            ("phone", "(097)98765", 422, samples.PHONE_PATTERN_MISMATCH_ERR),
            ("phone", "097-987-65", 422, samples.PHONE_PATTERN_MISMATCH_ERR),
            ("phone", "o979876543", 422, samples.PHONE_PATTERN_MISMATCH_ERR),
            ("phone", "+380979876", 422, samples.PHONE_PATTERN_MISMATCH_ERR),
            ("phone", "+380979876767", 422, samples.PHONE_NUMBER_TOO_LONG_ERR),
            ("phone", "+38097", 422, samples.PHONE_NUMBER_TOO_SHORT_ERR),
            ("name", "", 422, samples.NAME_TOO_SHORT_ERR),
            ("name", samples.COMPANY_NAME_101_SYMBOL, 422, samples.NAME_TOO_LONG_ERR),
            ("address", samples.COMPANY_ADDRESS_256_SYMBOLS, 422, samples.ADDRESS_TOO_LONG_ERR),
        ),
    )
    def test_contractor_creation_w_invalid_fields_values(
        self,
        client,
        system_user_auth_header,
        target_field_name,
        invalid_value,
        expected_status_code,
        expected_msg,
    ):
        """Test that with invalid body (wrong values of specific fields) the company won't be created with specific
        handling - appropriate status codes and messages.
        """
        invalid_body = deepcopy(samples.VALID_CONTRACTOR_BODY)
        invalid_body[target_field_name] = invalid_value

        response = client.post(self.CONTRACTORS_API_ENDPOINT, json=invalid_body, headers=system_user_auth_header)
        assert response.status_code == expected_status_code
        assert response.json()["message"] == expected_msg

    def test_contractor_duplicated_name(self, client, system_user_auth_header, db_session):
        payload = copy.deepcopy(samples.VALID_CONTRACTOR_BODY)
        payload["name"] = "Duplicated"
        creation_response1 = client.post(self.CONTRACTORS_API_ENDPOINT, json=payload, headers=system_user_auth_header)
        creation_response2 = client.post(self.CONTRACTORS_API_ENDPOINT, json=payload, headers=system_user_auth_header)

        clean_up_companies(db_session, "Duplicated")

        assert creation_response1.status_code == 201
        assert creation_response1.json() == {"code": 201, "message": "Company has been successfully created"}
        assert creation_response2.status_code == 409
        assert creation_response2.json()["message"] == samples.COMPANY_UNIQUE_NAME_CONSTRAINT_ERR

    def test_get_contractors(self, client, system_user_auth_header):
        """Test that companies GET endpoint works as expected: provides correct status, pagination,
        maintains default ordering by id field and typical body structure.
        """
        response = client.get(self.CONTRACTORS_API_ENDPOINT, headers=system_user_auth_header)
        response_json = response.json()

        # remove ID since it's dynamic field, only validates the companies were created
        response_items = response_json["items"]
        remove_dynamic_fields(response_items)

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert samples.VALID_CONTRACTOR_BODY in response_items

    def test_get_contractor_w_authz(self, client, non_system_user_auth_header):
        """Test that contractors GET endpoint detects non-system user and throws 403 for such admin-only endpoint."""
        response = client.get(self.CONTRACTORS_API_ENDPOINT, headers=non_system_user_auth_header)
        assert response.status_code == 403

    @pytest.mark.parametrize(
        "search_value",
        ("softserve", "contractor"),
    )
    def test_get_contractor_search(self, client, system_user_auth_header, search_value):
        """Test that companies GET endpoint with search parameter returns correct company."""
        response = client.get(
            self.CONTRACTORS_API_ENDPOINT, params={"search": search_value}, headers=system_user_auth_header
        )
        response_json = response.json()

        response_items = response_json["items"]
        remove_dynamic_fields(response_items)

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert samples.VALID_CONTRACTOR_BODY in response_items

    def test_get_contractors_search_not_existing(self, client, system_user_auth_header):
        """Test that companies GET endpoint with search parameter returns correct company."""
        response = client.get(
            self.CONTRACTORS_API_ENDPOINT, params={"search": "Non Existent Company"}, headers=system_user_auth_header
        )
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert len(response_json["items"]) == 0

    def test_get_contractors_by_id(self, client, system_user_auth_header, company_id):
        """Test that contractors fetch by id returns appropriate values as expected."""
        target_id = company_id
        response = client.get(f"{self.CONTRACTORS_API_ENDPOINT}/{target_id}", headers=system_user_auth_header)
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["name"] == samples.TEST_COMPANY_NAME
        assert response_json["email"] == samples.TEST_COMPANY_EMAIL
        assert response_json["address"] == samples.TEST_COMPANY_ADDRESS
        assert response_json["phone"] == samples.TEST_COMPANY_PHONE

    def test_get_contractors_by_id_404(self, client, system_user_auth_header, company_id):
        """Test that contractors GET with id of unexisting company gives 404."""
        # define non-existing company ID as next to created in the fixture
        company_id += 1
        response = client.get(f"{self.COMPANIES_API_ENDPOINT}/{company_id}", headers=system_user_auth_header)
        assert response.status_code == 404

    @pytest.mark.parametrize(
        ("target_field", "new_value"),
        (
            ("name", "NewCompany Somehow Incorporated"),
            ("email", "nvidia-assets-management@gmail.com"),
            ("phone", "6663629898"),
            ("address", "Plain street, 1, Nineveh, Assyria"),
        ),
    )
    def test_update_contractor(self, client, system_user_auth_header, target_field, new_value, company_id):
        """Test that a company can be updated with the new field values."""
        body, target_id = deepcopy(samples.TEST_COMPANY_PAYLOAD_JSON), company_id
        body.pop("company_type")
        body["name"] = "NewCompany Somehow Incorporated"
        body[target_field] = new_value

        put_response = client.put(
            f"{self.CONTRACTORS_API_ENDPOINT}/{target_id}", json=body, headers=system_user_auth_header
        )

        assert put_response.status_code == 202
        assert put_response.json()["message"] == "Company has been updated successfully"

        # fetch recently updated company by id and check new changes:
        response = client.get(f"{self.COMPANIES_API_ENDPOINT}/{target_id}", headers=system_user_auth_header)
        response_body = response.json()
        assert response_body[target_field] == new_value != samples.TEST_COMPANY_PAYLOAD_JSON[target_field]

    @pytest.mark.parametrize(
        ("target_field", "new_value", "expected_status_code", "expected_message"),
        (
            # the new name actually taken early by another company should be rejected:
            ("name", "Apple Inc.", 409, samples.COMPANY_UNIQUE_NAME_CONSTRAINT_ERR),
            # updating id value of the company entity should be disallowed:
            ("id", 109, 422, "Validation error: body.id - Extra inputs are not permitted"),
            # using email longer than 100 chars should be caught and disallowed by pydantic schema
            ("email", samples.LONGER_THAN_100_CHARS_EMAIL, 422, samples.EMAIL_LENGTH_ERROR),
            # unexpected fields in the company model schema should be disallowed:
            (
                "some_unexpected_field",
                "Spanish Inquisition",
                422,
                "Validation error: body.some_unexpected_field - Extra inputs are not permitted",
            ),
        ),
    )
    @pytest.mark.parametrize("setup_companies", [3], indirect=True)
    def test_update_with_disallowed_fields(
        self,
        client,
        system_user_auth_header,
        target_field,
        new_value,
        expected_status_code,
        expected_message,
        company_id,
        setup_companies,
    ):
        """Test that update of company specific fields is disallowed with specific handling - appropriate status
        codes and messages.
        """
        body, target_id = deepcopy(samples.VALID_CONTRACTOR_BODY), company_id
        body.pop("company_type")
        body[target_field] = new_value

        put_response = client.put(
            f"{self.CONTRACTORS_API_ENDPOINT}/{target_id}", json=body, headers=system_user_auth_header
        )
        assert put_response.status_code == expected_status_code
        assert put_response.json()["message"] == expected_message

    def test_update_contractor_not_found(self, client, system_user_auth_header):
        """Test update company for non-existent ID."""
        target_id = 123243454365465647
        payload = deepcopy(samples.VALID_CONTRACTOR_BODY)
        payload.pop("company_type")
        response = client.put(
            f"{self.CONTRACTORS_API_ENDPOINT}/{target_id}",
            json=payload,
            headers=system_user_auth_header,
        )

        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_update_contractor_403(self, client, company_id, non_system_user_auth_header):
        """Test update company with non admin user."""
        payload = deepcopy(samples.VALID_CONTRACTOR_BODY)
        payload.pop("company_type")
        response = client.put(
            f"{self.CONTRACTORS_API_ENDPOINT}/{company_id}",
            json=payload,
            headers=non_system_user_auth_header,
        )

        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_update_contractor_company_admin(self, client, company_id, company_admin_full_access_header):
        """Test update company with admin user."""
        payload = deepcopy(samples.VALID_CONTRACTOR_BODY)
        payload.pop("company_type")
        payload["name"] = "New Company Name"
        response = client.put(
            f"{self.CONTRACTORS_API_ENDPOINT}/{company_id}",
            json=payload,
            headers=company_admin_full_access_header,
        )

        assert response.status_code == 202
        assert response.json()["message"] == "Company has been updated successfully"

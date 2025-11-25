from copy import deepcopy

import pytest
from starlette import status

import app.static as static
from app.schema.role import RolesPaginator
from app.static.default_roles import MVP_ROLES
from tests.unit.samples.roles import DUMMY_PERMISSIONS, VALID_ROLE_BODY


class TestRoles:
    """Tests for roles routes."""

    ROLES_API_ENDPOINT = "/api/roles"
    ROLES_WITH_DEPENDENCIES_API_ENDPOINT = "/api/roles/with-company-type"
    ROLE_PERMISSIONS_ENDPOINT = "/api/roles/{role_id}/permissions"

    def test_roles_list(self, client, system_user_auth_header):
        response = client.get(self.ROLES_API_ENDPOINT, headers=system_user_auth_header)
        response_object = RolesPaginator(**response.json())
        assert response.status_code == status.HTTP_200_OK
        assert response_object.skip == static.DEFAULT_PAGINATION_SKIP
        assert response_object.limit == static.DEFAULT_PAGINATION_LIMIT
        assert response_object.total >= len(MVP_ROLES)
        # check roles are sorted by the very first expected role
        assert response_object.items[0].name == "Appraiser"
        assert response_object.items[0].company_type == "Appraiser"

    def test_shortened_roles_list(self, client, system_user_auth_header):
        response = client.get(self.ROLES_WITH_DEPENDENCIES_API_ENDPOINT, headers=system_user_auth_header)
        assert len(response.json()["data"]) >= len(MVP_ROLES)

    def test_create_role(self, client, system_user_auth_header):
        """Test that role created is successfully with valid payload."""
        response = client.post(self.ROLES_API_ENDPOINT, json=VALID_ROLE_BODY, headers=system_user_auth_header)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json() == {"code": status.HTTP_201_CREATED, "message": "Role has been created"}

    def test_role_creation_w_invalid_body(self, client, system_user_auth_header):
        """Test that with invalid body (missing essential field) the role won't be created and endpoint returns
        422 Unprocessable entity.
        """
        invalid_body = deepcopy(VALID_ROLE_BODY)
        del invalid_body["name"]

        response = client.post(self.ROLES_API_ENDPOINT, json=invalid_body, headers=system_user_auth_header)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.json() == {
            "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": "Validation error: body.name - Field required",
        }

    @pytest.mark.parametrize(
        ("target_field_name", "invalid_value", "expected_status_code", "expected_msg"),
        (
            (
                "name",
                123,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Validation error: body.name - Input should be a valid string",
            ),
            (
                "description",
                789,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Validation error: body.description - Input should be a valid string",
            ),
        ),
    )
    def test_role_creation_w_invalid_fields_values(
        self,
        client,
        system_user_auth_header,
        target_field_name,
        invalid_value,
        expected_status_code,
        expected_msg,
    ):
        """Test that with invalid body (wrong values of specific fields) the role won't be created with specific
        handling - appropriate status codes and messages.
        """
        invalid_body = deepcopy(VALID_ROLE_BODY)
        invalid_body[target_field_name] = invalid_value

        response = client.post(self.ROLES_API_ENDPOINT, json=invalid_body, headers=system_user_auth_header)
        assert response.status_code == expected_status_code
        assert response.json()["message"] == expected_msg

    def test_update_role(self, client, system_user_auth_header):
        """Test update role fields."""
        target_id = 1
        updated_role = {"name": "New role", "description": "Updated role description"}
        response = client.put(
            f"{self.ROLES_API_ENDPOINT}/{target_id}", json=updated_role, headers=system_user_auth_header
        )

        assert response.status_code == 202
        assert response.json()["message"] == "Role has been updated"

    def test_update_role_not_found(self, client, system_user_auth_header):
        """Test update role for non-existent ID."""
        target_id = 123243454365465647
        updated_role = {"name": "New role", "description": "Updated role description"}
        response = client.put(
            f"{self.ROLES_API_ENDPOINT}/{target_id}", json=updated_role, headers=system_user_auth_header
        )

        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_update_role_permissions(self, client, system_user_auth_header):
        """Test of PUT role's permissions."""
        target_id = 1
        response = client.put(
            self.ROLE_PERMISSIONS_ENDPOINT.format(role_id=target_id),
            json=DUMMY_PERMISSIONS,
            headers=system_user_auth_header,
        )

        assert response.status_code == 202
        assert response.json()["message"] == "Role's permissions have been updated"

        # check changes are in the effect
        get_response = client.get(self.ROLES_API_ENDPOINT, headers=system_user_auth_header)
        assert get_response.status_code == 200

        roles, target_role_permissions = get_response.json()["items"], None
        for role in roles:
            if role["id"] == target_id:
                target_role_permissions = role["permissions"]
        assert target_role_permissions == DUMMY_PERMISSIONS

    def test_update_permissions_w_role_not_found(self, client, system_user_auth_header):
        """Test update role's permissions for non-existent role ID."""
        target_id = 123243454365465647
        response = client.put(
            self.ROLE_PERMISSIONS_ENDPOINT.format(role_id=target_id),
            json=DUMMY_PERMISSIONS,
            headers=system_user_auth_header,
        )

        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

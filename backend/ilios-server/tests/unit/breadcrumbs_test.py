import pytest


class TestBreadcrumbs:
    @staticmethod
    def _generate_item_endpoint():
        return f"/api/breadcrumbs"

    @pytest.mark.parametrize(
        ("entity_type", "permission_module", "entity_parent_attr_name"),
        (
            ("company", "Asset Management", "random_attr_to_get_none"),
            ("site", "Asset Management", "company_id"),
            ("device", "Asset Management", "site_id"),
            ("document", "Asset Management", "site_id"),
            ("task", "Asset Management", "board_id"),
        ),
    )
    def test_get_breadcrumbs_entity_info(
        self,
        client,
        company,
        site,
        device,
        document,
        site_task,
        entity_type,
        permission_module,
        company_member_user,
        entity_parent_attr_name,
        company_member_user_auth_header,
    ):
        entity_type_mapper = {
            "company": company,
            "site": site,
            "device": device,
            "document": document,
            "task": site_task,
        }
        entity = entity_type_mapper[entity_type]
        parent_id = getattr(entity, entity_parent_attr_name, None)

        response = client.get(
            self._generate_item_endpoint(),
            headers=company_member_user_auth_header,
            params={"permission_module": permission_module, "entity_type": entity_type, "entity_id": entity.id},
        )
        expected_result = {
            "id": entity.id,
            "name": entity.name,
            "parent_id": parent_id,
            "parent_entity_type": entity_parent_attr_name.split("_")[0],
        }
        if entity_type == "document":
            expected_result["name"] = entity.name.value
        if entity_type == "task":
            expected_result["name"] = entity.external_id
        if entity_type == "company":
            expected_result["parent_entity_type"] = None
        response_json = response.json()
        assert response.status_code == 200
        assert response_json == expected_result

    @pytest.mark.parametrize(
        ("entity_type", "permission_module"),
        (
            ("company", "Asset Management"),
            (
                "site",
                "Asset Management",
            ),
            ("device", "Asset Management"),
            ("document", "Asset Management"),
            ("task", "Asset Management"),
        ),
    )
    def test_get_breadcrumbs_entity_info_403(
        self,
        client,
        company,
        site,
        device,
        document,
        site_task,
        entity_type,
        permission_module,
        non_system_user_auth_header,
        company_member_user_auth_header,
    ):
        entity_type_mapper = {
            "company": company,
            "site": site,
            "device": device,
            "document": document,
            "task": site_task,
        }
        entity = entity_type_mapper[entity_type]

        response = client.get(
            self._generate_item_endpoint(),
            headers=non_system_user_auth_header,
            params={"permission_module": permission_module, "entity_type": entity_type, "entity_id": entity.id},
        )
        assert response.status_code == 403

    @pytest.mark.parametrize(
        ("entity_type", "permission_module"),
        (
            ("company", "Asset Management"),
            ("site", "Asset Management"),
            ("device", "Asset Management"),
            ("document", "Asset Management"),
            ("task", "Asset Management"),
        ),
    )
    def test_get_breadcrumbs_entity_info_404(
        self,
        client,
        entity_type,
        permission_module,
        system_user_auth_header,
        company_member_user_auth_header,
    ):
        response = client.get(
            self._generate_item_endpoint(),
            headers=system_user_auth_header,
            params={"permission_module": permission_module, "entity_type": entity_type, "entity_id": 99999999},
        )
        assert response.status_code == 404

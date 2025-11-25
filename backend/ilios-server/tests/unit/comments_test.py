import pytest
from sqlalchemy import text

from app.static import PermissionsModules
from tests.utils import set_user_site_access


class TestComment:
    COMMENTS_ENDPOINT = "/api/comments"

    @pytest.mark.parametrize(
        "comment_entity_type,permission_module",
        # we need to call create comment API for all allowed entities
        # to ensure all scenarios from the comment helper were called
        (
            ("document", PermissionsModules.diligence.value),
            ("task", PermissionsModules.assets_management.value),
            ("document_key", PermissionsModules.diligence.value),
        ),
    )
    def test_post_comment_entity_not_found(
        self, client, company_member_user_auth_header, comment_entity_type, permission_module
    ):
        response = client.post(
            self.COMMENTS_ENDPOINT,
            json={
                "text": "Test comment",
                # use large ID number here, do not interfere in other tests
                "entity_id": 100,
                "entity_type": comment_entity_type,
            },
            headers=company_member_user_auth_header,
            params={"permission_module": permission_module},
        )
        assert response.status_code == 404
        assert response.json()["message"] == f"Commented entity {comment_entity_type} with id 100 not found"

    @pytest.mark.parametrize(
        ("auth_header_getter,comment_entity_type,permission_module"),
        (
            # system user
            (
                lambda system_user_auth_header, non_system_user_auth_header: system_user_auth_header,
                "document",
                PermissionsModules.diligence.value,
            ),
            (
                lambda system_user_auth_header, non_system_user_auth_header: system_user_auth_header,
                "task",
                PermissionsModules.assets_management.value,
            ),
            (
                lambda system_user_auth_header, non_system_user_auth_header: system_user_auth_header,
                "document_key",
                PermissionsModules.diligence.value,
            ),
            # non-system user
            (
                lambda system_user_auth_header, non_system_user_auth_header: non_system_user_auth_header,
                "document",
                PermissionsModules.diligence.value,
            ),
            (
                lambda system_user_auth_header, non_system_user_auth_header: non_system_user_auth_header,
                "task",
                PermissionsModules.assets_management.value,
            ),
            (
                lambda system_user_auth_header, non_system_user_auth_header: non_system_user_auth_header,
                "document_key",
                PermissionsModules.diligence.value,
            ),
        ),
    )
    def test_post_comment(
        self,
        client,
        system_user_auth_header,
        company_member_user_auth_header,
        document,
        site_task,
        site_lease_document_key,
        auth_header_getter,
        comment_entity_type,
        permission_module,
        site_id,
    ):
        entity_id_mapper = {
            "document": document.id,
            "task": site_task.id,
            "document_key": site_lease_document_key.id,
        }
        entity_id = entity_id_mapper[comment_entity_type]
        response = client.post(
            self.COMMENTS_ENDPOINT,
            json={
                "text": "What is the capital of Assyria?",
                "entity_id": entity_id,
                "entity_type": comment_entity_type,
            },
            headers=auth_header_getter(system_user_auth_header, company_member_user_auth_header),
            params={"permission_module": permission_module},
        )
        assert response.status_code == 201
        assert response.json()["message"] == "Comment has been successfully added"

    def test_post_comment_text_too_long(self, client, company_member_user_auth_header, document, company_member_user):
        response = client.post(
            self.COMMENTS_ENDPOINT,
            json={
                "text": "Test comment" * 1000,
                "entity_id": document.id,
                "entity_type": "document",
            },
            headers=company_member_user_auth_header,
            params={"permission_module": PermissionsModules.diligence.value},
        )
        assert response.status_code == 422
        assert response.json()["message"] == "Validation error: body.text - String should have at most 1000 characters"

    def test_post_comment_403(self, client, non_system_user_auth_header, document):
        response = client.post(
            self.COMMENTS_ENDPOINT,
            json={"text": "What is the capital of Assyria?", "entity_id": document.id, "entity_type": "document"},
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403

    @pytest.mark.parametrize(
        "auth_header_getter",
        (
            # system user
            lambda system_user_auth_header, non_system_user_auth_header: system_user_auth_header,
            # non-system user
            lambda system_user_auth_header, non_system_user_auth_header: non_system_user_auth_header,
        ),
    )
    def test_get_comments(
        self,
        client,
        system_user_auth_header,
        company_member_user_auth_header,
        comment,
        auth_header_getter,
        site_id,
    ):
        entity_id, entity_type = comment.commented_entity.entity_id, comment.commented_entity.entity_type.value
        response = client.get(
            self.COMMENTS_ENDPOINT,
            headers=auth_header_getter(system_user_auth_header, company_member_user_auth_header),
            params={
                "entity_id": entity_id,
                "entity_type": entity_type,
                "permission_module": PermissionsModules.diligence.value,
            },
        )
        assert response.status_code == 200

        response = response.json()
        items = response["items"]

        target_item = None
        for item in items:
            if item["id"] == comment.id:
                target_item = item
                break

        assert target_item is not None
        assert target_item["text"] == "Dummy comment about something completely different"
        assert target_item["first_name"] == "Deleted"
        assert target_item["last_name"] == "User"

        assert response["skip"] == 0
        assert response["limit"] == 10
        assert response["total"] >= 1

    def test_get_comments_403(self, client, non_system_user_auth_header, comment):
        entity_id, entity_type = comment.commented_entity.entity_id, comment.commented_entity.entity_type.value
        response = client.get(
            self.COMMENTS_ENDPOINT,
            headers=non_system_user_auth_header,
            params={"entity_id": entity_id, "entity_type": entity_type},
        )

        assert response.status_code == 403

    def test_get_comments_of_unexisting_document(self, client, system_user_auth_header):
        response = client.get(
            self.COMMENTS_ENDPOINT,
            headers=system_user_auth_header,
            params={"entity_id": 999999, "entity_type": "document"},
        )

        assert response.status_code == 404

    @pytest.mark.parametrize(
        "skip,limit",
        (
            (-1, 10),
            (1, -10),
            (-1, -10),
            (9223372036854775808, 1),
            (1, 9223372036854775808),
            (9223372036854775808, 9223372036854775808),
        ),
    )
    def test_get_comments_invalid_skip_limit(self, client, comment, company_member_user_auth_header, skip, limit):
        """Validate scenarios from the bug IOSP1-1061"""
        entity_id, entity_type = comment.commented_entity.entity_id, comment.commented_entity.entity_type.value
        response = client.get(
            self.COMMENTS_ENDPOINT,
            headers=company_member_user_auth_header,
            params={"entity_id": entity_id, "entity_type": entity_type, "skip": skip, "limit": limit},
        )
        assert response.status_code == 400
        assert (
            response.json()["message"]
            == "It is required skip/limit input be a valid positive number and no longer than 9223372036854775807."
        )

    @pytest.mark.parametrize(
        "mentioned_users_ids,expected_error",
        (
            # validate mentions are list
            ("not-a-list", "Validation error: body.mentioned_users_ids - Input should be a valid list"),
            # validate mentions are list of integers
            (
                ["not-an-int"],
                "Validation error: body.mentioned_users_ids.0 - Input should be a valid integer, "
                "unable to parse string as an integer",
            ),
        ),
    )
    def test_post_comment_with_tag_validation_error(
        self,
        client,
        company_member_user_auth_header,
        document,
        site_lease_document_key,
        mentioned_users_ids,
        expected_error,
    ):
        response = client.post(
            self.COMMENTS_ENDPOINT,
            json={
                "text": "Comment with mention",
                "entity_id": document.id,
                "entity_type": "document",
                "mentioned_users_ids": mentioned_users_ids,
            },
            headers=company_member_user_auth_header,
            params={"permission_module": PermissionsModules.diligence.value},
        )
        assert response.status_code == 422
        assert response.json()["message"] == expected_error

    @pytest.mark.parametrize(
        "comment_entity_type,entity_getter_key,permission_module",
        (
            ("document", "document", PermissionsModules.diligence.value),
            ("task", "site_task", PermissionsModules.assets_management.value),
            ("task", "company_task", PermissionsModules.operation_maintenance.value),
            ("document_key", "document_key", PermissionsModules.diligence.value),
        ),
    )
    def test_post_comment_with_tag_user_403(
        self,
        client,
        company_member_user_auth_header,
        document,
        site_task,
        company_om_task,
        site_lease_document_key,
        comment_entity_type,
        entity_getter_key,
        permission_module,
    ):
        """For all possible commented entities, validate comment adding is failed
        if mentioning users doesn't have access to the commented entity"""
        entity_id_mapper = {
            "document": document.id,
            "site_task": site_task.id,
            "company_task": company_om_task.id,
            "document_key": site_lease_document_key.id,
        }
        entity_id = entity_id_mapper[entity_getter_key]
        response = client.post(
            self.COMMENTS_ENDPOINT,
            json={
                "text": "Comment with mention",
                "entity_id": entity_id,
                "entity_type": comment_entity_type,
                "mentioned_users_ids": [1],
            },
            headers=company_member_user_auth_header,
            params={"permission_module": permission_module},
        )
        assert response.status_code == 400
        assert (
            response.json()["message"]
            == "Some of users you're trying to tag do not have access to the commented resource"
        )

    @pytest.mark.parametrize(
        "comment_entity_type,entity_getter_key,permission_module",
        (
            ("document", "document", PermissionsModules.diligence),
            ("task", "site_task", PermissionsModules.assets_management),
            ("task", "company_task", PermissionsModules.assets_management),
            ("document_key", "document_key", PermissionsModules.diligence),
        ),
    )
    def test_post_comment_with_tag_success(
        self,
        client,
        company_member_user_auth_header,
        document,
        site_task,
        company_task,
        site_lease_document_key,
        comment_entity_type,
        entity_getter_key,
        permission_module,
        company_member_user,
        create_non_system_user,
        db_session,
        role_id,
    ):
        # we need to set access for these users explicitly
        company_member_user.is_registered = True
        create_non_system_user.role_id = role_id
        db_session.commit()
        set_user_site_access(db_session=db_session, site=site_task.board.related_entity.entity, user=company_member_user)
        set_user_site_access(
            db_session=db_session, site=site_task.board.related_entity.entity, user=create_non_system_user
        )
        entity_id_mapper = {
            "document": document.id,
            "site_task": site_task.id,
            "company_task": company_task.id,
            "document_key": site_lease_document_key.id,
        }
        entity_id = entity_id_mapper[entity_getter_key]
        response = client.post(
            self.COMMENTS_ENDPOINT,
            json={
                "text": "Comment with mention",
                "entity_id": entity_id,
                "entity_type": comment_entity_type,
                "mentioned_users_ids": [company_member_user.id, create_non_system_user.id],
            },
            headers=company_member_user_auth_header,
            params={"permission_module": permission_module},
        )
        assert response.status_code == 201

        # clean up created notifications to not affect other tests
        db_session.execute(text("DELETE FROM notifications WHERE kind = 'comment_mention';"))

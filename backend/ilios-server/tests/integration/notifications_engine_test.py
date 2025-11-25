import copy
from unittest.mock import MagicMock, call

import pytest

import tests.unit.samples as samples
from app.crud.user import UserCRUD
from app.models.notification import NotificationKindsEnum
from app.static import PermissionsModules
from tests.utils import set_user_site_access


class TestTasksNotificationsTriggers:
    """The test case runs update on the task object to validate task notifications adding were triggered.
    There is no need to test task related APIs, just DB changes regarding the notifications"""

    @staticmethod
    def _generate_task_details_endpoint(board_id_, task_id_):
        """api/task-tracker/boards/{BOARD_ID}/tasks/TASK_ID/details"""
        return f"api/task-tracker/boards/{board_id_}/tasks/{task_id_}/details"

    def test_task_status_changed_notification(
        self,
        db_session,
        client,
        site_default_board,
        site_task,
        company_member_user,
        company_member_user_auth_header,
        non_system_user_id,
        mocker,
    ):
        """Validate if task status was changed notification for the task creator was added,
        otherwise no notification added"""
        notification_crud_spy = mocker.patch(
            "app.helpers.notification_helper.NotificationCRUD.create_item", return_value=MagicMock(id=1)
        )
        notification_subject_crud_spy = mocker.patch(
            "app.helpers.notification_helper.NotificationSubjectCRUD.create_item",
        )
        payload = samples.make_task_details_payload(site_default_board, non_system_user_id)

        # no notification case
        payload_without_change = copy.deepcopy(payload)
        payload_without_change["status_id"] = site_task.status.id

        client.put(
            f"{self._generate_task_details_endpoint(site_default_board.id, site_task.id)}",
            headers=company_member_user_auth_header,
            json=payload_without_change,
        )
        notification_crud_spy.assert_not_called()

        # notification added case
        payload_with_change = copy.deepcopy(payload)
        # ensure status differs from the previous update
        payload_with_change["status_id"] = [
            status_id
            for status_id in site_default_board.get_statuses_ids()
            if status_id != payload_without_change["status_id"]
        ][0]

        client.put(
            f"{self._generate_task_details_endpoint(site_default_board.id, site_task.id)}",
            headers=company_member_user_auth_header,
            json=payload_with_change,
        )
        notification_crud_spy.assert_called_once_with(
            {
                "actor_id": company_member_user.id,
                "kind": NotificationKindsEnum.task_status_change.value,
                "recipient_id": site_task.creator_id,
                "extra": {"status_id": payload_with_change["status_id"]},
            }
        )
        notification_subject_crud_spy.assert_called_once_with(
            {"entity_id": site_task.id, "entity_type": "task", "notification_id": 1}
        )

    def test_task_unassigned_notification(
        self,
        db_session,
        client,
        site_default_board,
        site_task,
        company_member_user,
        company_member_user_auth_header,
        non_system_user_id,
        mocker,
    ):
        """Validate if task was unassigned notification for the task creator was added,
        otherwise no notification added"""
        notification_crud_spy = mocker.patch(
            "app.helpers.notification_helper.NotificationCRUD.create_item", return_value=MagicMock(id=1)
        )
        notification_subject_crud_spy = mocker.patch(
            "app.helpers.notification_helper.NotificationSubjectCRUD.create_item",
        )
        payload = samples.make_task_details_payload(site_default_board, non_system_user_id)

        # no notification case
        payload_without_change = copy.deepcopy(payload)
        client.put(
            f"{self._generate_task_details_endpoint(site_default_board.id, site_task.id)}",
            headers=company_member_user_auth_header,
            json=payload_without_change,
        )
        notification_crud_spy.assert_not_called()

        # notification added case
        payload_with_change = copy.deepcopy(payload)
        payload_with_change["assignee_id"] = None

        client.put(
            f"{self._generate_task_details_endpoint(site_default_board.id, site_task.id)}",
            headers=company_member_user_auth_header,
            json=payload_with_change,
        )

        notification_crud_spy.assert_called_once_with(
            {
                "actor_id": company_member_user.id,
                "kind": NotificationKindsEnum.task_assignee_unset.value,
                "recipient_id": site_task.creator_id,
                "extra": {"previous_assignee_id": site_task.assignee_id},
            }
        )
        assert payload_without_change["assignee_id"] is not None
        assert payload_with_change["assignee_id"] is None
        notification_subject_crud_spy.assert_called_once_with(
            {"entity_id": site_task.id, "entity_type": "task", "notification_id": 1}
        )

    def test_task_assigned_notification(
        self,
        db_session,
        client,
        site_default_board,
        site_task,
        company_member_user,
        company_member_user_auth_header,
        non_system_user_id,
        mocker,
    ):
        """Validate if task was assigned notification for the new assignee was added,
        as well as for the task creator if task was assigned previously for someone else"""
        notification_crud_spy = mocker.patch(
            "app.helpers.notification_helper.NotificationCRUD.create_item",
        )
        notification_handler_spy = mocker.patch(
            "app.routers.task_tracker.tasks.NotificationHandler.save_notification",
        )
        payload = samples.make_task_details_payload(site_default_board, non_system_user_id)

        # no notification case
        payload_without_change = copy.deepcopy(payload)
        client.put(
            f"{self._generate_task_details_endpoint(site_default_board.id, site_task.id)}",
            headers=company_member_user_auth_header,
            json=payload_without_change,
        )
        notification_crud_spy.assert_not_called()

        # notification added case - assign the task to the company admin user, and validate
        # - creator got notification
        # attempt to create notification for company admin user was made
        # (but it wasn't created because the company admin did change by themselves)
        payload_with_change = copy.deepcopy(payload)
        # we need to have company member user registered to pass the assignee_id validation
        UserCRUD(db_session).update_by_id(company_member_user.id, {"is_registered": True})
        payload_with_change["assignee_id"] = company_member_user.id

        client.put(
            f"{self._generate_task_details_endpoint(site_default_board.id, site_task.id)}",
            headers=company_member_user_auth_header,
            json=payload_with_change,
        )

        notification_handler_spy.assert_has_calls(
            [
                # assignee notification
                call(recipient_id=company_member_user.id, kind=NotificationKindsEnum.task_assignee_added),
                # creator notification
                call(
                    recipient_id=site_task.creator_id,
                    kind=NotificationKindsEnum.task_assignee_changed,
                    extra={"new_assignee_id": company_member_user.id},
                ),
            ],
            any_order=True,
        )


class TestCommentNotificationsTriggers:
    """The task case runs comment creation for each of the comment types: document, tasks, document key"""

    COMMENTS_ENDPOINT = "/api/comments"

    @pytest.mark.parametrize(
        "comment_entity_type,entity_getter_key,permissions_module",
        (
            ("document", "document", PermissionsModules.diligence.value),
            ("task", "site_asset_task", PermissionsModules.assets_management.value),
            ("task", "site_om_task", PermissionsModules.operation_maintenance.value),
            ("task", "company_task", PermissionsModules.assets_management.value),
            ("task", "company_om_task", PermissionsModules.operation_maintenance.value),
            ("document_key", "document_key", PermissionsModules.diligence.value),
        ),
    )
    def test_comment_mention_notification(
        self,
        db_session,
        client,
        company_member_user,
        company_member_user_auth_header,
        mocker,
        comment_entity_type,
        entity_getter_key,
        permissions_module,
        create_non_system_user,
        site_task,
        site_om_task,
        company_task,
        company_om_task,
        site_lease_document,
        site_lease_document_key,
        role_id,
    ):
        """Validate if comment has mention notification was added, otherwise no notification added"""
        entity_id_mapper = {
            "document": site_lease_document.id,
            "site_asset_task": site_task.id,
            "site_om_task": site_om_task.id,
            "company_task": company_task.id,
            "company_om_task": company_om_task.id,
            "document_key": site_lease_document_key.id,
        }
        entity_id = entity_id_mapper[entity_getter_key]
        # we need to set access for these users explicitly
        company_member_user.is_registered = True
        create_non_system_user.role_id = role_id
        db_session.commit()
        set_user_site_access(db_session=db_session, site=site_task.board.related_entity.entity, user=company_member_user)
        set_user_site_access(
            db_session=db_session, site=site_task.board.related_entity.entity, user=create_non_system_user
        )

        # mock DB calls related to the comment creation
        mocker.patch("app.routers.comments.CommentCRUD.create_item", return_value=MagicMock(id=1))
        mocker.patch("app.routers.comments.CommentedEntityCRUD.create_item", return_value=MagicMock(id=1))
        mocker.patch("app.routers.comments.CommentMentionCRUD.create_items")
        # create spys on the DB calls we want to validate
        notification_crud_spy = mocker.patch(
            "app.helpers.notification_helper.NotificationCRUD.create_item", return_value=MagicMock(id=1)
        )
        notification_subject_crud_spy = mocker.patch(
            "app.helpers.notification_helper.NotificationSubjectCRUD.create_item",
        )

        # no notification case - no people mentioned
        payload_no_mention = {
            "text": "Test comment",
            "entity_id": entity_id,
            "entity_type": comment_entity_type,
        }

        client.post(
            self.COMMENTS_ENDPOINT,
            headers=company_member_user_auth_header,
            json=payload_no_mention,
            params={"permission_module": permissions_module},
        )
        notification_crud_spy.assert_not_called()

        # notification added case
        payload_with_mention = copy.deepcopy(payload_no_mention)
        payload_with_mention["mentioned_users_ids"] = [company_member_user.id, create_non_system_user.id]
        payload_with_mention["extra"] = {"file_id": 1}

        client.post(
            self.COMMENTS_ENDPOINT,
            headers=company_member_user_auth_header,
            json=payload_with_mention,
            params={"permission_module": permissions_module},
        )
        # Note! We attempt to create mention 2 person, but actual notification added only for 2nd since 1st is actor
        notification_crud_spy.assert_called_once_with(
            {
                "actor_id": company_member_user.id,
                "kind": NotificationKindsEnum.comment_mention.value,
                "recipient_id": create_non_system_user.id,
                "extra": {"file_id": 1},
            }
        )
        notification_subject_crud_spy.assert_called_once_with(
            {"entity_id": 1, "entity_type": "comment", "notification_id": 1}
        )

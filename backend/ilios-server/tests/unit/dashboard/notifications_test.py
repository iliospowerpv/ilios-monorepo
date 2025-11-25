from app.models.notification import NotificationKindsEnum
from app.static import TASK_UNDEFINED_STATUS, NotificationMessages


class TestNotificationsDashboard:
    @staticmethod
    def _generate_list_endpoint():
        return "/api/account/dashboard/notifications"

    @staticmethod
    def _generate_individual_endpoint(notification_id):
        return f"/api/account/dashboard/notifications/{notification_id}"

    @staticmethod
    def _generate_mark_as_read_endpoint(notification_id):
        return f"/api/account/dashboard/notifications/{notification_id}/seen"

    def test_get_notifications_list(
        self,
        client,
        company_member_notifications,
        company_member_user_auth_header,
        company_task,
        site_default_board,
        site_task,
        create_non_system_user,
        site_lease_document,
        site_lease_document_key,
        company,
        site,
    ):
        response = client.get(
            self._generate_list_endpoint(),
            headers=company_member_user_auth_header,
        )

        response_items = response.json()["items"]

        # 1. Task related notifications
        # validate notifications about status change has extras with status
        status_change_notifications_extras = [
            notification["extra"]
            for notification in response_items
            if notification["kind"] == NotificationKindsEnum.task_status_change.name
        ]
        status_key_assert = all(
            ["status" in status_change_notification for status_change_notification in status_change_notifications_extras]
        )
        expected_statuses_extras = [{"status": TASK_UNDEFINED_STATUS}, {"status": site_default_board.statuses[0].name}]

        # validate company level task notifications has empty site, but has company values set
        company_level_task_notifications = [
            notification
            for notification in response_items
            if notification.get("task") and notification["task"]["id"] == company_task.id
        ]
        company_level_task_notification_empty_site_details_assert = all(
            [(notification["site"] is None) for notification in company_level_task_notifications]
        )
        expected_company_payload = {
            "id": company_task.board.related_entity.entity.id,
            "name": company_task.board.related_entity.entity.name,
        }
        company_level_task_notification_company_name_assert = all(
            [(notification["company"] == expected_company_payload) for notification in company_level_task_notifications]
        )

        # validate site level task notifications has both site and company details
        site_level_task_notifications = [
            notification
            for notification in response_items
            if notification.get("task") and notification["task"]["id"] == site_task.id
        ]
        expected_site_payload = {
            "id": site_task.board.related_entity.entity.id,
            "name": site_task.board.related_entity.entity.name,
        }
        site_level_task_notification_site_details_assert = all(
            [(notification["site"] == expected_site_payload) for notification in site_level_task_notifications]
        )
        expected_company_payload_site_level_tasks = {
            "id": site_task.board.related_entity.entity.company.id,
            "name": site_task.board.related_entity.entity.company.name,
        }
        site_level_task_notification_company_details_assert = all(
            [
                (notification["company"] == expected_company_payload_site_level_tasks)
                for notification in site_level_task_notifications
            ]
        )

        # validate notification actor is either user or deleted user
        non_system_user_actor = {
            "id": create_non_system_user.id,
            "first_name": create_non_system_user.first_name,
            "last_name": create_non_system_user.last_name,
        }
        undefined_actor = {"id": None, "first_name": "Deleted", "last_name": "User"}
        notification_actor_assert = all(
            [
                (notification["actor"] == non_system_user_actor or notification["actor"] == undefined_actor)
                for notification in response_items
            ]
        )

        # validate notifications about un-assignment has extras with previous_assignee
        assignee_unset_notifications_extras = [
            notification["extra"]
            for notification in response_items
            if notification["kind"] == NotificationKindsEnum.task_assignee_unset.name
        ]
        previous_assignee_key_assert = all(
            [
                "previous_assignee" in assignee_unset_notification
                for assignee_unset_notification in assignee_unset_notifications_extras
            ]
        )

        # validate notifications about changed assignee has extras with new_assignee
        assignee_changed_notifications_extras = [
            notification["extra"]
            for notification in response_items
            if notification["kind"] == NotificationKindsEnum.task_assignee_changed.name
        ]
        new_assignee_key_assert = all(
            [
                "new_assignee" in assignee_changed_notification
                for assignee_changed_notification in assignee_changed_notifications_extras
            ]
        )

        # 2. Comment related notifications
        # validate comment related notifications has comment object populated,
        # and it's represent text and related entities
        comment_mentions_notifications = [
            notification
            for notification in response_items
            if notification["kind"] == NotificationKindsEnum.comment_mention.name
        ]
        comment_mentions_notifications_comment = [
            notification["comment"] for notification in comment_mentions_notifications
        ]
        expected_comment_mentions_notifications_comment = [
            {"text": "Document key mention", "entity_type": "document_key", "entity_id": site_lease_document_key.id},
            {"text": "Site task mention", "entity_type": "task", "entity_id": site_task.id},
            {"text": "Company task mention", "entity_type": "task", "entity_id": company_task.id},
            {"text": "Document mention", "entity_type": "document", "entity_id": site_lease_document.id},
        ]

        # validate all comment notifications has company info
        comment_mentions_notifications_company_details_assert = all(
            [
                notification["company"] == {"id": company.id, "name": company.name}
                for notification in comment_mentions_notifications
            ]
        )

        # validate all comment notifications except company level task related have site info
        comment_mentions_notifications_site_details_assert = all(
            [
                notification["site"] == {"id": site.id, "name": site.name}
                for notification in comment_mentions_notifications
                if notification["comment"]
                != {"text": "Company task mention", "entity_type": "task", "entity_id": company_task.id}
            ]
        )

        # validate notifications about mention on the document key
        # has both file_id and document_id details in the extras
        document_key_mention_notification = [
            notification
            for notification in comment_mentions_notifications
            if notification["comment"]["entity_type"] == "document_key"
        ][0]
        document_key_mention_notification_extras_asset = (
            "document_id" in document_key_mention_notification["extra"]
            and "file_id" in document_key_mention_notification["extra"]
        )

        # validate notifications about mentions on the task has task details populated
        task_mention_notifications = [
            notification
            for notification in comment_mentions_notifications
            if notification["comment"]["entity_type"] == "task"
        ]
        task_mention_notifications_has_task_details_assert = all(
            [
                "id" in notification["task"] and "external_id" in notification["task"]
                for notification in task_mention_notifications
            ]
        )

        # 3. Common
        # validate notifications which has tasks has it name, external id and module
        notifications_with_task_object_populated = [
            notification for notification in response_items if notification["task"] is not None
        ]
        notification_with_tasks_fields_asset = all(
            [
                notification["task"]["id"] is not None
                and notification["task"]["external_id"] is not None
                and notification["task"]["module"] is not None
                for notification in notifications_with_task_object_populated
            ]
        )

        assert response.status_code == 200
        assert response.json()["total"] == len(company_member_notifications)
        assert response.json()["unread_count"] == len(company_member_notifications)
        assert status_key_assert
        assert status_change_notifications_extras == expected_statuses_extras
        assert company_level_task_notification_empty_site_details_assert
        assert company_level_task_notification_company_name_assert
        assert site_level_task_notification_site_details_assert
        assert site_level_task_notification_company_details_assert
        assert notification_actor_assert
        assert previous_assignee_key_assert
        assert new_assignee_key_assert
        assert comment_mentions_notifications_comment == expected_comment_mentions_notifications_comment
        assert comment_mentions_notifications_company_details_assert
        assert comment_mentions_notifications_site_details_assert
        assert document_key_mention_notification_extras_asset
        assert task_mention_notifications_has_task_details_assert
        assert notification_with_tasks_fields_asset

        # validate notifications are ordered by their creation descending
        assert response_items[0]["created_at"] > response_items[-1]["created_at"]

    def test_get_notifications_list_empty(self, client, company_member_notifications, non_system_user_auth_header):
        """Validate user receive empty list if they are not notification recipients"""
        response = client.get(
            self._generate_list_endpoint(),
            headers=non_system_user_auth_header,
        )

        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["total"] == 0

    def test_mark_notification_as_read(
        self,
        client,
        notification,
        company_member_user_auth_header,
        db_session,
    ):
        assert notification.seen is False

        response = client.patch(
            self._generate_mark_as_read_endpoint(notification.id),
            headers=company_member_user_auth_header,
        )
        db_session.refresh(notification)
        assert response.status_code == 202
        assert response.json()["message"] == NotificationMessages.mark_as_read_success.value
        assert notification.seen is True

    def test_mark_notification_as_read_403(self, client, notification, non_system_user_auth_header):
        response = client.patch(
            self._generate_mark_as_read_endpoint(notification.id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403

    def test_mark_notification_as_read_404(self, client, non_system_user_auth_header):
        response = client.patch(
            self._generate_mark_as_read_endpoint(9999),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 404

    def test_delete_notification(
        self,
        client,
        notification,
        company_member_user_auth_header,
        db_session,
    ):
        response = client.delete(
            self._generate_individual_endpoint(notification.id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json()["message"] == NotificationMessages.delete_success.value

    def test_delete_notification_403(self, client, notification, non_system_user_auth_header):
        response = client.delete(
            self._generate_individual_endpoint(notification.id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403

    def test_delete_notification_404(self, client, non_system_user_auth_header):
        response = client.delete(
            self._generate_individual_endpoint(9999),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 404

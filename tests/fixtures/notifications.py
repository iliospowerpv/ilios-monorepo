import copy

import pytest

from app.crud.comment import CommentCRUD
from app.crud.commented_entity import CommentedEntityCRUD
from app.crud.notification import NotificationCRUD
from app.crud.notification_subject import NotificationSubjectCRUD
from app.models.notification import NotificationKindsEnum


@pytest.fixture(scope="function")
def company_member_notifications(
    db_session,
    site_default_board,
    company_member_user,
    non_system_user_id,
    site_task_id,
    company_task,
    site_lease_document,
    site_lease_document_key,
    site_om_task,
    company_om_task,
):
    """Create all available notifications assigned to the non system user"""
    notification_crud = NotificationCRUD(db_session)
    notification_subject_crud = NotificationSubjectCRUD(db_session)

    comment_crud = CommentCRUD(db_session)
    commented_entity_crud = CommentedEntityCRUD(db_session)
    # Task-related notifications
    task_notifications_to_add = []

    notification_payload_base = {
        "actor_id": non_system_user_id,
        "recipient_id": company_member_user.id,
    }

    # status change notification - should have status ID as extra
    status_change_notification_valid = copy.deepcopy(notification_payload_base)
    status_change_notification_valid.update(
        {
            "kind": NotificationKindsEnum.task_status_change,
            "extra": {"status_id": site_default_board.get_statuses_ids()[0]},
        }
    )
    task_notifications_to_add.append((status_change_notification_valid, site_task_id))
    # status change notification - if status was deleted, but still mentioned
    status_change_notification_status_deleted = copy.deepcopy(notification_payload_base)
    status_change_notification_status_deleted.update(
        {"kind": NotificationKindsEnum.task_status_change, "extra": {"status_id": -1}}
    )
    task_notifications_to_add.append((status_change_notification_status_deleted, site_task_id))

    # task assigned notification - also emulate case if actor was removed, site O&M task
    task_assigned_notification = copy.deepcopy(notification_payload_base)
    del task_assigned_notification["actor_id"]
    task_assigned_notification.update(
        {
            "kind": NotificationKindsEnum.task_assignee_added,
        }
    )
    task_notifications_to_add.append((task_assigned_notification, site_om_task.id))

    # task unassigned notification - based on the company level task
    task_unassigned_notification = copy.deepcopy(notification_payload_base)
    task_unassigned_notification.update(
        {
            "kind": NotificationKindsEnum.task_assignee_unset,
            "extra": {"previous_assignee_id": company_task.assignee_id},
        }
    )
    task_notifications_to_add.append((task_unassigned_notification, company_task.id))

    # task assignee changed notification
    task_assignee_changed_notification = copy.deepcopy(notification_payload_base)
    task_assignee_changed_notification.update(
        {
            "kind": NotificationKindsEnum.task_assignee_changed,
            "extra": {"new_assignee_id": -1},
        }
    )
    task_notifications_to_add.append((task_assignee_changed_notification, site_task_id))
    # and the same for the O&M company task
    task_notifications_to_add.append((task_assignee_changed_notification, company_om_task.id))

    # Comments related notifications
    comment_mention_notification = copy.deepcopy(notification_payload_base)
    comment_mention_notification["kind"] = NotificationKindsEnum.comment_mention
    # for the comment notifications, we need to create comment and comment related entity
    # NOTE! Since this is not API call, comment mentions table will not be populated
    document_comment = comment_crud.create_item({"text": "Document mention"})
    commented_entity_crud.create_item(
        {
            "comment_id": document_comment.id,
            "entity_type": "document",
            "entity_id": site_lease_document.id,
        }
    )
    document_key_comment = comment_crud.create_item({"text": "Document key mention"})
    commented_entity_crud.create_item(
        {
            "comment_id": document_key_comment.id,
            "entity_type": "document_key",
            "entity_id": site_lease_document_key.id,
        }
    )
    company_task_comment = comment_crud.create_item({"text": "Company task mention"})
    commented_entity_crud.create_item(
        {
            "comment_id": company_task_comment.id,
            "entity_type": "task",
            "entity_id": company_task.id,
        }
    )
    site_task_comment = comment_crud.create_item({"text": "Site task mention"})
    commented_entity_crud.create_item(
        {
            "comment_id": site_task_comment.id,
            "entity_type": "task",
            "entity_id": site_task_id,
        }
    )

    # append prefixes
    task_notifications_to_add = [
        (*task_notification_payload, "task") for task_notification_payload in task_notifications_to_add
    ]
    comment_notifications_to_add = [
        (comment_mention_notification, comment_id, "comment")
        for comment_id in [document_comment.id, company_task_comment.id, site_task_comment.id]
    ]
    # additionally process notification with extra
    document_key_comment_mention_notification = copy.deepcopy(comment_mention_notification)
    document_key_comment_mention_notification["extra"] = {"file_id": 1}
    comment_notifications_to_add.append((document_key_comment_mention_notification, document_key_comment.id, "comment"))

    notification_to_add = task_notifications_to_add + comment_notifications_to_add

    # create notifications without bulk operation to have objects for further usage
    notifications = []
    for notification_payload, entity_id, entity_type in notification_to_add:
        notification = notification_crud.create_item(notification_payload)
        notification_subject_crud.create_item(
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "notification_id": notification.id,
            }
        )
        notifications.append(notification)

    yield notifications

    for db_notification in notifications:
        notification_crud.delete_by_id(db_notification.id)


@pytest.fixture(scope="function")
def notification(company_member_notifications):
    yield company_member_notifications[0]

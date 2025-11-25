import logging

from sqlalchemy.orm import Session

from app.crud.notification import NotificationCRUD
from app.crud.notification_subject import NotificationSubjectCRUD
from app.crud.user import UserCRUD
from app.models.board import BoardRelatedEntityTypeEnum
from app.models.comment import CommentedEntityTypeEnum
from app.models.notification import Notification, NotificationKindsEnum, NotificationSubjectsEnum
from app.schema.user import CurrentUserSchema
from app.static import TASK_DELETED_USER, TASK_UNDEFINED_STATUS

logger = logging.getLogger(__name__)


class NotificationHandler:

    def __init__(
        self,
        db_session: Session,
        actor: CurrentUserSchema,
        notification_subject: NotificationSubjectsEnum,
        notification_subject_id: int,
    ):
        self.db_session = db_session
        self.actor = actor
        self.notification_subject = notification_subject
        self.notification_subject_id = notification_subject_id

    def save_notification(self, recipient_id: int, kind: NotificationKindsEnum, extra: dict = None):  # noqa: FNE003
        """Create and save notification object of specific type with ability to pass extra arguments"""
        # do not send notification if actor and recipient are the same person
        if self.actor.id == recipient_id:
            return
        notification_data = {
            "actor_id": self.actor.id,
            "recipient_id": recipient_id,
            "kind": kind.value,
        }
        # save additional notification metadata
        if extra:
            notification_data["extra"] = extra
        notification_obj = NotificationCRUD(db_session=self.db_session).create_item(notification_data)
        NotificationSubjectCRUD(self.db_session).create_item(
            {
                "entity_id": self.notification_subject_id,
                "entity_type": self.notification_subject,
                "notification_id": notification_obj.id,
            }
        )
        logger.info(f"The <{kind.value}> notification has been added with id={notification_obj.id}")


class NotificationReadHandler:
    """Process notification to populate additional fields before the Pydantic serialization"""

    def __init__(self, notification: Notification, db_session: Session):
        self.notification = notification
        self.db_session = db_session
        self.notification_subject = self._retrieve_notification_subject()

    def _retrieve_notification_subject(self):
        """As part of notification init, retrieve related object"""
        subject_object = None
        if self.notification.subject.entity_type == NotificationSubjectsEnum.task:
            subject_object = self.notification.subject.parent_entity_task
            subject_object.module = subject_object.board.module
            self.notification.task = subject_object
        elif self.notification.subject.entity_type == NotificationSubjectsEnum.comment:
            subject_object = self.notification.subject.parent_entity_comment
            # for comment, explicitly set commented entity attributes
            subject_object.entity_id = subject_object.commented_entity.entity_id
            subject_object.entity_type = subject_object.commented_entity.entity_type
            self.notification.comment = subject_object
        return subject_object

    @staticmethod
    def _prepare_related_entity_obj(entity):
        """Create object with name and ID, to represent company/site details in the notification"""
        return {
            "id": entity.id,
            "name": entity.name,
        }

    def _set_task_related_entity(self, task):
        if task.board.related_entity.entity_type == BoardRelatedEntityTypeEnum.company:
            # for the company level tasks, set company details
            self.notification.company = self._prepare_related_entity_obj(task.board.related_entity.entity)
        elif task.board.related_entity.entity_type == BoardRelatedEntityTypeEnum.site:
            # for the site level tasks, set both site and company details
            self.notification.site = self._prepare_related_entity_obj(task.board.related_entity.entity)
            self.notification.company = self._prepare_related_entity_obj(task.board.related_entity.entity.company)

    def set_related_entity(self):
        """Based on the notification subject, populate linked entities details.
        * We distinguish two types of tasks - on the Company and on the Site level.
        * As well as 3 types of comments: on the document, on the document key and on the task level (also, be aware:
        task comments also divided by the task level - company or site"""
        # task notifications
        if self.notification.subject.entity_type == NotificationSubjectsEnum.task:
            self._set_task_related_entity(task=self.notification_subject)
        # comments notifications
        elif self.notification.subject.entity_type == NotificationSubjectsEnum.comment:
            if self.notification_subject.entity_type == CommentedEntityTypeEnum.document_key:
                # for the document key comments, set company and site based on the parent document data
                document = self.notification_subject.commented_entity.parent_entity_documentkey.document
                self.notification.site = self._prepare_related_entity_obj(document.site)
                self.notification.company = self._prepare_related_entity_obj(document.site.company)
                # extend extras with document id
                extras = self.notification.extra or {}
                self.notification.extra = extras | {"document_id": document.id}
            elif self.notification_subject.entity_type == CommentedEntityTypeEnum.document:
                # for the document comments, set company and site based on the site data
                document = self.notification_subject.commented_entity.parent_entity_document
                self.notification.site = self._prepare_related_entity_obj(document.site)
                self.notification.company = self._prepare_related_entity_obj(document.site.company)
            elif self.notification_subject.entity_type == CommentedEntityTypeEnum.task:
                # for the task comments, reuse the same logic as for the task level notifications
                task = self.notification_subject.commented_entity.parent_entity_task
                task.module = task.board.module
                self._set_task_related_entity(task=task)
                # also, we need to populate task details for proper routing
                self.notification.task = task

    def _get_status_details(self):
        """Get new task status name"""
        board_statuses = []
        if self.notification.subject.entity_type == NotificationSubjectsEnum.task:
            board_statuses = self.notification_subject.board.statuses
        status_obj = [
            board_status for board_status in board_statuses if board_status.id == self.notification.extra["status_id"]
        ]
        # since statuses are manageable, handle case if it was deleted, but still mentioned in the notification
        return status_obj[0].name if status_obj else TASK_UNDEFINED_STATUS

    def _get_user_details(self, extra_key_name):
        """Get DB user first/last name or return Deleted User if cannot lookup user"""
        user_obj = UserCRUD(self.db_session).get_by_id(self.notification.extra[extra_key_name])
        return f"{user_obj.first_name} {user_obj.last_name}" if user_obj else TASK_DELETED_USER

    def set_extras(self):
        if self.notification.extra:
            extras = {}
            if "status_id" in self.notification.extra:
                extras["status"] = self._get_status_details()
            if "previous_assignee_id" in self.notification.extra:
                extras["previous_assignee"] = self._get_user_details("previous_assignee_id")
            if "new_assignee_id" in self.notification.extra:
                extras["new_assignee"] = self._get_user_details("new_assignee_id")
            if "file_id" in self.notification.extra:
                extras["file_id"] = self.notification.extra["file_id"]
            if "document_id" in self.notification.extra:
                extras["document_id"] = self.notification.extra["document_id"]
            self.notification.extra = extras

    def extend_with_additional_fields(self):
        """To support templates, set additional fields for the notification"""
        self.set_related_entity()
        self.set_extras()

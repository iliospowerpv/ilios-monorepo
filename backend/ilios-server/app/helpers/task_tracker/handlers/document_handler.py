import logging

from app.crud.task import TaskCRUD
from app.filters.user_filters import UserSearchForTaskFilter
from app.helpers.roles_documents_mapping.handlers_factory import RoleDocumentsHandlerFactory

from .base_handler import TaskTrackerBaseHandler

logger = logging.getLogger(__name__)


class DocumentTasksHandler(TaskTrackerBaseHandler):
    def _get_assignees_params(self):
        """For the document level board, assignees are specified as users with access to the current site"""
        return {"site_id": self.board.related_entity.entity_id}

    def get_assignees(self, search_user_filter: UserSearchForTaskFilter = None, task_id: int = None):
        """Extend base class method with filter by the document access"""
        # get assignees by the main class query
        assignees = super().get_assignees(search_user_filter)
        # To keep FE working, return full list if filtering query doesn't come
        # TODO return empty assignees list if no task_id provided, after FE implements it
        # TODO create tech debt ticket for it
        if not task_id:
            return assignees

        # if task_id provided - validate task defined properly and document attached
        task = TaskCRUD(self.db_session).get_by_id(task_id)

        if not task:
            logger.warning(f"There is no task with id <{task_id}>")
            return []

        if task.board_id != self.board.id:
            logger.warning(
                f"Invalid task_id provided, task with id <{task_id}> doesn't belong to the board "
                f"with id <{self.board.id}>"
            )
            return []

        if not task.document:
            logger.warning(f"Invalid task_id provided, task with id <{task_id}> doesn't have linked DD document")
            return []

        # by attached document details get roles who should have access to it
        output_roles_ids = RoleDocumentsHandlerFactory.get_available_roles_by_document(
            document=task.document, db_session=self.db_session
        )

        # filter base class assignees according to the roles document access
        filtered_assignees = [assignee for assignee in assignees if assignee[-1] in output_roles_ids]

        return filtered_assignees

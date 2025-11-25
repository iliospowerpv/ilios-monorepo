import logging

from .base_handler import TaskTrackerBaseHandler

logger = logging.getLogger(__name__)


class CompanyTasksHandler(TaskTrackerBaseHandler):
    def _get_assignees_params(self):
        return {"company_id": self.board.related_entity.entity_id}

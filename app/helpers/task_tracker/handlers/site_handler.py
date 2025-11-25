import logging

from fastapi import HTTPException, status

from app.models.board import BoardModuleEnum
from app.static import BoardMessages

from .base_handler import TaskTrackerBaseHandler

logger = logging.getLogger(__name__)


class SiteTasksHandler(TaskTrackerBaseHandler):

    def _get_assignees_params(self):
        return {"site_id": self.board.related_entity.entity_id}

    def _validate_affected_device_id(self, affected_device_id):
        if affected_device_id not in self.board.related_entity.entity.get_affected_devices_ids():
            logger.warning(
                f"The device with id {affected_device_id} is not allowed to be assigned to the task as affected device "
                f"on the board with id {self.board.id}: device either doesn't exist or is not related to the site "
                f"with id {self.board.related_entity.entity_id}."
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid affected device ID")

    def _validate_alert_id(self, alert_id):
        # Alert tasks can be created only for Site O&M boards
        if self.board.module != BoardModuleEnum.om:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=BoardMessages.invalid_alert_task_board)
        if alert_id not in self.board.related_entity.entity.get_alerts_ids():
            logger.warning(
                f"The alert with id {alert_id} is not allowed to be assigned to the task "
                f"on the board with id {self.board.id}: alert either doesn't exist or is not related to the site "
                f"with id {self.board.related_entity.entity_id}."
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid alert ID")

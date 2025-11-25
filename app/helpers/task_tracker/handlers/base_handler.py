import logging
from abc import ABC, abstractmethod
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud.task import TaskCRUD
from app.crud.user_project import UserProjectCRUD
from app.filters.user_filters import UserSearchForTaskFilter
from app.models.board import Board, BoardModuleEnum, BoardRelatedEntityTypeEnum, BoardRelatedEntityTypeExtraEnum
from app.models.helpers import utcnow
from app.static import (
    DEFAULT_BOARD_PREFIX,
    BoardMessages,
    CompanyBoardDefaultStatuses,
    DocumentBoardDefaultStatuses,
    PermissionsModules,
    SiteBoardDefaultStatuses,
)

logger = logging.getLogger(__name__)


class TaskTrackerBaseHandler(ABC):

    def __init__(self, related_entity_type: BoardRelatedEntityTypeEnum, board: Board, db_session: Session):
        self.related_entity_type = related_entity_type
        self.board = board
        self.board_statuses = self._define_default_statuses()
        self.db_session = db_session
        self.module_name_verbose = self._define_module_name_verbose()
        self.completion_statuses = self._define_completion_statuses()

    def _define_completion_statuses(self):
        """Map statuses which are treated as completed to the board types"""
        module_permission_mapping = {
            BoardModuleEnum.asset: ["Closed", "Cancelled"],
            BoardModuleEnum.om: ["Closed", "Cancelled"],
            BoardModuleEnum.diligence: ["Completed"],
        }
        return module_permission_mapping[self.board.module]

    def _define_module_name_verbose(self):
        """Map internal board module to its correspondence from Role permissions names"""
        module_permission_mapping = {
            BoardModuleEnum.asset: PermissionsModules.assets_management.value,
            BoardModuleEnum.diligence: PermissionsModules.diligence.value,
            BoardModuleEnum.om: PermissionsModules.operation_maintenance.value,
        }
        return module_permission_mapping[self.board.module]

    def _define_default_statuses(self):
        """Different entities have different boards and statuses,
        * site - asset and o&m, statuses are different;
        * company - asset and o&m, statuses are the same;
        * document - diligence"""
        entity_dependent_board_statuses = {
            BoardRelatedEntityTypeEnum.company: CompanyBoardDefaultStatuses,
            BoardRelatedEntityTypeExtraEnum.document: DocumentBoardDefaultStatuses,
        }
        site_modules_board_statuses = {
            BoardModuleEnum.asset: SiteBoardDefaultStatuses,
            BoardModuleEnum.om: CompanyBoardDefaultStatuses,
        }
        if self.related_entity_type in [BoardRelatedEntityTypeEnum.company, BoardRelatedEntityTypeExtraEnum.document]:
            return entity_dependent_board_statuses[self.related_entity_type]
        elif self.related_entity_type == BoardRelatedEntityTypeEnum.site:
            return site_modules_board_statuses[self.board.module]

    def get_default_statuses(self):
        return [{"name": board_status, "board_id": self.board.id} for board_status in self.board_statuses.list()]

    def get_assignees(self, search_user_filter: UserSearchForTaskFilter = None, task_id: int = None):  # noqa: U100
        """Retrieve potential board assignees, filtered by the module with search available.
        args:
            search_user_filter - search filter, used in all boards
            task_id - id of task to extend the Document board method,
                but we need to keep it in the signature for base class method
        """
        user_project_crud = UserProjectCRUD(self.db_session)
        params = self._get_assignees_params()
        params.update({"search_filter": search_user_filter, "module": self.module_name_verbose})
        assignees = user_project_crud.get_potential_task_assignees(**params)
        return assignees

    def get_board_active_users_ids(self, task_id: int = None):
        """Retrieve only assignees IDs from <self.get_assignees> method"""
        return [user.id for user in self.get_assignees(task_id=task_id)]

    @abstractmethod
    def _get_assignees_params(self):
        """Based on the board related entity type, specify assignees filter option:
        - site_id for the Site and Document boards
        - company_id for the Company board"""

    def validate_task_related_entities_existence(self, task):
        """Pre-validation of the task related objects before DB operations processing"""
        self.validate_task_assignee_id(task)
        self.validate_task_status_against_board_statuses(task)
        self.validate_affected_device_id(task)
        self.validate_task_alert_id(task)

    def validate_task_assignee_id(self, task, task_id=None):
        """Retrieve assignee IDs according to the board entity type and check if input ID is allowed"""
        if task.assignee_id:
            assignees_ids = self.get_board_active_users_ids(task_id)
            if task.assignee_id not in assignees_ids:
                logger.warning(
                    f"The user with id {task.assignee_id} is not allowed to be assigned to the task on the board "
                    f"with id {self.board.id}: user either doesn't complete the registration or doesn't have access "
                    f"to the {self.board.related_entity.entity_type} with id {self.board.related_entity.entity_id}."
                )
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid assignee ID")

    def validate_task_status_against_board_statuses(self, task):
        """Validate task status among allowed board statuses"""
        if task.status_id not in self.board.get_statuses_ids():
            logger.warning(f"Status with id {task.status_id} doesn't belong to the board with id {self.board.id}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status ID")

    def validate_affected_device_id(self, task):
        """Validate affected device id if it's in the request"""
        if task.affected_device_id:
            # Make sure affected device applicable only for the site level boards
            if self.board.related_entity.entity_type != BoardRelatedEntityTypeEnum.site:
                task.affected_device_id = None
            else:
                self._validate_affected_device_id(task.affected_device_id)

    def validate_task_alert_id(self, task):
        """Validate affected alert id if it's in the request"""
        if task.alert_id:
            self._validate_alert_id(task.alert_id)

    def _validate_affected_device_id(self, affected_device_id):  # noqa: U100
        """Currently implemented only for the Site level handler"""

    def _validate_alert_id(self, alert_id):  # noqa: U100
        """Currently implemented only for the Site. For all other handlers raise exception"""
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=BoardMessages.invalid_alert_task_board)

    @staticmethod
    def validate_task_due_date(task):
        if not task.due_date >= date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Due Date: value must be a date of today or date in future",
            )

    def generate_task_external_id(self, task_crud: TaskCRUD, board_prefix=DEFAULT_BOARD_PREFIX, max_prefix_counter=1):
        max_prefix_number = self.get_task_max_prefix_number(task_crud, board_prefix)
        return self._get_external_task_id(max_prefix_number, max_prefix_counter, board_prefix)

    @staticmethod
    def get_task_max_prefix_number(task_crud: TaskCRUD, board_prefix=DEFAULT_BOARD_PREFIX):
        return task_crud.get_max_prefix_number(board_prefix) or 0

    @staticmethod
    def _get_external_task_id(max_prefix_number: int, max_prefix_counter: int, board_prefix=DEFAULT_BOARD_PREFIX):
        return f"{board_prefix}-{max_prefix_number + max_prefix_counter}"

    def validate_updated_task_related_entities(self, old_task, new_task):
        if old_task.assignee_id != new_task.assignee_id:
            self.validate_task_assignee_id(new_task, task_id=old_task.id)
        if old_task.affected_device_id != new_task.affected_device_id:
            self.validate_affected_device_id(new_task)
        if old_task.due_date != new_task.due_date:
            self.validate_task_due_date(new_task)
        self.validate_task_status_against_board_statuses(new_task)

    def update_task_completion_details(self, task):
        """If task status has been changed for the status we should treat as completion - set completed_at as
        the current datetime, if task already was completed, but status changed back - cleanup completion_at"""
        if task.status.name in self.completion_statuses:
            task.completed_at = utcnow()
            self.db_session.commit()
            return

        # if task was completed, but new status is not in the completion - unset completion
        if task.completed_at:
            task.completed_at = None
            self.db_session.commit()

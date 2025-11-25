from sqlalchemy.orm import Session

from app.models.board import Board, BoardRelatedEntityTypeEnum, BoardRelatedEntityTypeExtraEnum

from .company_handler import CompanyTasksHandler
from .document_handler import DocumentTasksHandler
from .site_handler import SiteTasksHandler


class TaskTrackerHandlerFactory:

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_instance(self, board: Board):
        """Based on the related entity type, return instance of dedicated board handler"""
        related_entity_type = board.related_entity.entity_type
        if (
            related_entity_type == BoardRelatedEntityTypeEnum.site
            and board.related_entity.extra_entity_type == BoardRelatedEntityTypeExtraEnum.document
        ):
            related_entity_type = BoardRelatedEntityTypeExtraEnum.document
        init_params = {"related_entity_type": related_entity_type, "board": board, "db_session": self.db_session}
        available_instances = {
            BoardRelatedEntityTypeEnum.site: SiteTasksHandler,
            BoardRelatedEntityTypeEnum.company: CompanyTasksHandler,
            BoardRelatedEntityTypeExtraEnum.document: DocumentTasksHandler,
        }
        instance = available_instances.get(related_entity_type)
        return instance(**init_params)

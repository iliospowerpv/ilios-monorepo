from app.crud.base_crud import BaseCRUD
from app.models.board import Board, BoardRelatedEntity, BoardRelatedEntityTypeEnum
from app.static import DEFAULT_PAGINATION_LIMIT, DEFAULT_PAGINATION_SKIP


class BoardRelatedEntityCRUD(BaseCRUD):
    """CRUD operations on BoardRelatedEntity model."""

    def __init__(self, db_session):
        super().__init__(model=BoardRelatedEntity, db_session=db_session)

    def get_by_entity(
        self, entity_type, entity_id, module, skip: int = DEFAULT_PAGINATION_SKIP, limit: int = DEFAULT_PAGINATION_LIMIT
    ):
        query = self.db_session.query(
            Board.id,
            self.model.entity_id,
            Board.name,
            Board.description,
            Board.is_active,
            Board.module,
        )
        query = query.join(Board, self.model.board_id == Board.id)
        query = query.filter(
            self.model.entity_type == entity_type, self.model.entity_id == entity_id, Board.module == module
        )
        query = self._add_order_by(query, Board.created_at, order_direction="desc")
        total = query.count()
        return total, query.offset(skip).limit(limit).all()

    def get_entity_default_board(self, entity_id, entity_type: BoardRelatedEntityTypeEnum):
        """Get default board for given entity type Company/Site."""
        query = self.db_session.query(
            Board.id,
            self.model.entity_id,
            self.model.board_id,
            Board.name,
            Board.is_active,
        )
        query = query.join(Board, self.model.board_id == Board.id)
        query = query.filter(self.model.entity_type == entity_type, self.model.entity_id == entity_id)
        query = query.filter(Board.name == "Default board")
        query = query.filter(Board.is_active)

        return query.first()

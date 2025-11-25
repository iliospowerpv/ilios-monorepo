from sqlalchemy import func
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.functions import coalesce

from app.crud.base_crud import BaseCRUD
from app.models.comment import Comment, CommentedEntity
from app.models.user import User
from app.static import DEFAULT_PAGINATION_LIMIT, DEFAULT_PAGINATION_SKIP


class CommentedEntityCRUD(BaseCRUD):
    """CRUD operations on CommentedEntity model."""

    def __init__(self, db_session):
        super().__init__(model=CommentedEntity, db_session=db_session)

    def get_by_entity(
        self, entity_type, entity_id, skip: int = DEFAULT_PAGINATION_SKIP, limit: int = DEFAULT_PAGINATION_LIMIT
    ):
        query = self.db_session.query(
            Comment.id,
            self.model.entity_id,
            Comment.text,
            Comment.created_at,
            Comment.updated_at,
            coalesce(User.first_name, "Deleted").label("first_name"),
            coalesce(User.last_name, "User").label("last_name"),
        )
        query = query.join(Comment, self.model.comment_id == Comment.id).outerjoin(User, Comment.user_id == User.id)
        query = query.filter(self.model.entity_type == entity_type, self.model.entity_id == entity_id)
        query = self._add_order_by(query, Comment.id, order_direction="desc")

        total = query.count()
        return total, query.offset(skip).limit(limit).all()

    def get_by_entities_grouped(self, entity_type, entities_ids):
        """Get comments grouped by the entity ID"""

        comment_subquery = func.json_agg(
            postgresql.aggregate_order_by(
                func.json_build_object(
                    "id",
                    Comment.id,
                    "entity_id",
                    self.model.entity_id,
                    "text",
                    Comment.text,
                    "created_at",
                    Comment.created_at,
                    "updated_at",
                    Comment.updated_at,
                    "first_name",
                    func.coalesce(User.first_name, "Deleted"),
                    "last_name",
                    func.coalesce(User.last_name, "User"),
                ),
                Comment.id.desc(),
            )
        ).label("comments")
        query = self.db_session.query(
            self.model.entity_id,
            comment_subquery,
        )
        query = query.join(Comment, self.model.comment_id == Comment.id).outerjoin(User, Comment.user_id == User.id)
        query = query.filter(self.model.entity_type == entity_type, self.model.entity_id.in_(entities_ids))
        query = query.group_by(self.model.entity_id)

        return query.all()

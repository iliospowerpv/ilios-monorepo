"""Base repo location."""

import logging
from abc import ABCMeta
from typing import Iterable, List, Optional

from psycopg2 import errors as psycopg_errors
from sqlalchemy import Enum, String, asc, cast, desc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import InstrumentedAttribute, Session

import app.static as static
from app.crud.errors import UniqueConstraintViolationError
from app.db.base_class import Base
from app.models.helpers import utcnow

logger = logging.getLogger(__name__)


class BaseCRUD(metaclass=ABCMeta):
    """Repository pattern implementation for typical CRUD operation on DB entities using SQLAlchemy."""

    def __init__(self, model: Base, db_session: Session):
        self.model = model
        self.db_session = db_session

    def total(self) -> int:
        """Retrieve total records in the table.
        :return: integer
        """
        return self.db_session.query(func.count(self.model.id)).scalar()

    def create_item(self, item: dict) -> Base:
        """Create item.

        :param item: dict with full item body to be used for creation
        :return: ORM-wrapped item
        """
        item_model = self.model(**item)
        try:
            self.db_session.add(item_model)
            self.db_session.commit()
        except IntegrityError as exc:
            self.db_session.rollback()
            if isinstance(exc.orig, psycopg_errors.UniqueViolation):
                raise UniqueConstraintViolationError(message=exc.args[0])
            raise

        return item_model

    def create_items(self, items: Iterable) -> None:
        """Create items.

        :param items: iterable of dicts with full item bodies to be used for creation
        :return: None
        """
        try:
            self.db_session.bulk_save_objects(self.model(**item) for item in items)
            self.db_session.commit()
        except IntegrityError as exc:
            self.db_session.rollback()
            if isinstance(exc.orig, psycopg_errors.UniqueViolation):
                raise UniqueConstraintViolationError(message=exc.args[0])
            raise

    def get_by_id(self, target_id):
        """Get item by target id.

        :param target_id: primary key of target
        :return: ORM-wrapped item
        """
        return self.db_session.get(self.model, target_id)

    def get(
        self,
        skip: int = static.DEFAULT_PAGINATION_SKIP,
        limit: int = static.DEFAULT_PAGINATION_LIMIT,
        order_by: Optional[str] = None,
        skip_pagination: bool = False,
    ) -> List[Base]:
        """Get all items with applied skip (offset) and limits, by default sorted/ordered ascending by pk.

        :param skip: number of items to skip (offset)
        :param limit: number of items to get per page
        :param order_by: field name to order by
        :param skip_pagination: indicated if output should be limited
        :return: list of items
        """
        query = self.db_session.query(self.model).order_by(
            order_by if order_by else self.model.__table__.primary_key.columns
        )
        if skip_pagination:
            return query.all()

        return query.offset(skip).limit(limit).all()

    def bulk_get_by_id(self, ids):
        """Return several items by provided IDs"""
        return self.db_session.query(self.model).filter(self.model.id.in_(ids)).all()

    def update_by_id(self, target_id, item: dict) -> int:
        """Update item by target id.

        :param target_id: primary key of target
        :param item: dict with full item body to be used for update
        :return: updated count (1 if matched and updated or 0 if not found)
        """
        # Always refresh updated_at on update operations, if this field exists in the model
        if "updated_at" in self.model.__table__.columns:
            item["updated_at"] = utcnow()
        try:
            updated_count = self.db_session.query(self.model).filter_by(id=target_id).update(item)
            self.db_session.commit()
            return updated_count
        except IntegrityError as exc:
            self.db_session.rollback()
            # such approach couples BaseCRUD to postgres. If you want to avoid it just parse sqlalchemy err msg instead,
            # like: message=exc.args[0]; if 'Key' in message and 'already exists' in message: raise Error.
            if isinstance(exc.orig, psycopg_errors.UniqueViolation):
                raise UniqueConstraintViolationError(message=exc.args[0])
            raise

    def update(self, items: Iterable):  # noqa U100
        raise NotImplementedError

    def delete_by_id(self, target_id) -> int:
        """Delete item by target id.

        :param target_id: primary key of target
        :return: deleted count (1 if deleted or 0 if not found)
        """
        deleted_count = self.db_session.query(self.model).filter_by(id=target_id).delete()

        if deleted_count == 0:
            return deleted_count  # nothing to commit, return early
        self.db_session.commit()
        return deleted_count

    def delete(self, target_ids: Optional[Iterable] = None):  # noqa U100
        """Delete multiple items.

        :param target_ids: primary keys of targets
        :return:
        """
        raise NotImplementedError

    def _add_order_by(self, query, order_by, order_direction):
        """Add custom ordering for the query if it was requested. If not - return default ordering by the PK field"""
        if not order_by:
            return query.order_by(self.model.__table__.primary_key.columns)

        order_direction_clause = desc if order_direction == "desc" else asc
        # Handle ordering by Enum field as by String
        # Check if Model field type is sqlalchemy.Enum and cast it as String to get correct ordering
        # If order_by is already a Model field check if it is InstrumentedAttribute
        order_by_model_field = (
            order_by if type(order_by) is InstrumentedAttribute else getattr(self.model, order_by, None)
        )
        if order_by_model_field and type(order_by_model_field.type) is Enum:
            return query.order_by(order_direction_clause(cast(order_by_model_field, String)))
        else:
            return query.order_by(order_direction_clause(order_by))

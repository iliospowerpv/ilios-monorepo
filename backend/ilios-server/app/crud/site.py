"""CRUD operations on Site model."""

from typing import List, Optional, Tuple

from fastapi_filter.contrib.sqlalchemy import Filter
from sqlalchemy import or_

import app.static as static
from app.crud.base_crud import BaseCRUD
from app.db.base_class import Base
from app.models.company import Company
from app.models.site import Site
from app.schema.common import OrderDirectionEnum
from app.schema.site import SiteOrderByFieldEnum


class SiteCRUD(BaseCRUD):
    """CRUD operations on Site model."""

    def __init__(self, db_session):
        super().__init__(model=Site, db_session=db_session)

    def filter(
        self,
        sites_ids: set | None,
        site_filter: Filter | None = None,
        skip: int = static.DEFAULT_PAGINATION_SKIP,
        limit: int = static.DEFAULT_PAGINATION_LIMIT,
        order_by: Optional[str] = SiteOrderByFieldEnum.name.value,
        order_direction: Optional[str] = OrderDirectionEnum.asc.value,
    ) -> Tuple[int, List[Base]]:
        """Get all items with applied filters,  skip (offset) and limits, sorted ascending by pk.

        :param sites_ids: non-fastapi-wrapped filter
        :param site_filter: filter to apply
        :param skip: number of items to skip (offset)
        :param limit: number of items to get per page
        :param order_by: field name to order by
        :param order_direction: direction clause to order by (asc or desc)
        :return: list of items
        """
        # we need to define default values explicitly, since they came as NULL because of validate_query_params
        order_by = order_by or SiteOrderByFieldEnum.name.value
        order_direction = order_direction or OrderDirectionEnum.asc.value
        query = self.db_session.query(self.model)
        if sites_ids is not None:
            query = query.filter(self.model.id.in_(sites_ids))
        if order_by == SiteOrderByFieldEnum.company_name:
            order_by = "name"
            query = query.outerjoin(Company)
        if site_filter:
            query = site_filter.filter(query)
        query = self._add_order_by(query, order_by, order_direction)
        total = query.count()
        return total, query.offset(skip).limit(limit).all()

    def get_sites_by_company_id(  # noqa: CFQ002
        self,
        company_id: int,
        search_filter: Filter | None = None,
        skip: int = static.DEFAULT_PAGINATION_SKIP,
        limit: int = static.DEFAULT_PAGINATION_LIMIT,
        order_by: Optional[str] = None,
        order_direction: Optional[str] = None,
        skip_pagination: bool = False,
        site_ids_to_limit: Optional[list] = None,
    ) -> Tuple[int, List[Base]]:
        query = self.db_session.query(self.model)
        if search_filter:
            query = search_filter.filter(query)
        query = query.filter(self.model.company_id == company_id)
        if site_ids_to_limit:
            query = query.filter(self.model.id.in_(site_ids_to_limit))
        query = self._add_order_by(query, order_by, order_direction)
        total = query.count()
        if skip_pagination:
            return total, query.all()
        return total, query.offset(skip).limit(limit).all()

    def get_sites_for_settings(
        self,
        search: str | None,
        skip: int = static.DEFAULT_PAGINATION_SKIP,
        limit: int = static.DEFAULT_PAGINATION_LIMIT,
        order_by: Optional[str] = None,
        order_direction: Optional[str] = None,
    ) -> (int, List[Base]):
        """Get all items with applied filters,  skip (offset) and limits, sorted ascending by pk.

        :param search: search field by name or company_name
        :param skip: number of items to skip (offset)
        :param limit: number of items to get per page
        :param order_by: field name to order by
        :param order_direction: direction clause to order by (asc or desc)
        :return: tuple of total and items list
        """
        query = self.db_session.query(
            self.model.id,
            self.model.company_id,
            # duplicate column name labels so that alchemy don't use the same columns from joined tables
            self.model.name.label("name"),
            self.model.address.label("address"),
            Company.name.label("company_name"),
        )
        query = query.outerjoin(Company)
        if search is not None:
            query = query.filter(or_(self.model.name.ilike(f"%{search}%"), Company.name.ilike(f"%{search}%")))
        query = self._add_order_by(query, order_by, order_direction)
        total = query.count()
        return total, query.offset(skip).limit(limit).all()

    def get_all_sites_ids(self):
        """Retrieve IDs of all sites in the platform as a list"""
        queryset = self.db_session.query(
            self.model.id,
        ).all()
        return [row[0] for row in queryset]

    def get_sites_location(self):
        """Retrieve all site ids with site location lon_lat_url"""
        query = self.db_session.query(self.model.id, self.model.lon_lat_url)
        return query.all()

"""CRUD operations on Company model."""

from typing import List, Optional

from fastapi_filter.contrib.sqlalchemy import Filter
from sqlalchemy import and_, case, func, or_

import app.static as static
from app.crud.base_crud import BaseCRUD
from app.db.base_class import Base
from app.models.company import Company
from app.models.site import Site, SiteAdditionalFieldList, SiteStatuses
from app.schema.common import OrderDirectionEnum
from app.schema.company import CompaniesOrderByFieldEnum
from app.static.companies import CompanyTypes


class CompanyCRUD(BaseCRUD):
    """CRUD operations on Company model."""

    def __init__(self, db_session):
        super().__init__(model=Company, db_session=db_session)

    @staticmethod
    def _build_system_size_clause(field_name):
        """Build statement to sum input system size attr only for sites which have <Placed in Service> status"""
        return func.coalesce(
            # sum returns null by default, coalesce it to 0
            func.sum(
                case(
                    (SiteAdditionalFieldList.status.in_([SiteStatuses.placed_in_service.name]), field_name),
                )
            ),
            0,
        )

    def get_with_sites_info(
        self,
        company_ids: List[int] | None = None,
        skip: int = static.DEFAULT_PAGINATION_SKIP,
        limit: int = static.DEFAULT_PAGINATION_LIMIT,
        order_by: Optional[str] = None,
        order_direction: Optional[str] = None,
        search_filter: Filter | None = None,
        site_ids_to_limit: list | None = None,
        include_archived: bool = False,
        archived_only: bool = False,
    ):
        """Get all companies with joined cumulative sites info like total_sites count and total_capacity. Also, applies
        skip (offset) and limits, sorts ascending by pk.

        :param company_ids: list of user company IDs
        :param skip: number of items to skip (offset)
        :param limit: number of items to get per page
        :param order_by: field name to order by
        :param order_direction: direction clause to order by (asc or desc)
        :param search_filter: search value
        :param include_archived: if True, include archived companies
        :param archived_only: if True, show only archived companies
        :return: tuple of total and items list
        """
        # we need to define default values explicitly, since they came as NULL because of validate_query_params
        order_by = order_by or CompaniesOrderByFieldEnum.name.value
        order_direction = order_direction or OrderDirectionEnum.asc.value
        query = self.db_session.query(
            self.model.id.label("id"),
            self.model.name.label("name"),
            func.count(Site.id).label("total_sites"),
            self._build_system_size_clause(Site.system_size_ac).label("total_capacity"),
            # return company site IDs
            func.array_agg(Site.id).label("sites_ids"),
            self.model.is_archived.label("is_archived"),
        )
        if archived_only:
            query = query.filter(self.model.is_archived == True)
        elif not include_archived:
            query = query.filter(self.model.is_archived == False)
        if company_ids is not None:
            query = query.filter(self.model.id.in_(company_ids))
        if search_filter:
            query = search_filter.filter(query)
        query = query.outerjoin(Site, and_(self.model.id == Site.company_id, Site.is_archived == False)).join(
            SiteAdditionalFieldList, SiteAdditionalFieldList.site_id == Site.id, isouter=True
        )
        if site_ids_to_limit:
            query = query.filter(or_(Site.id == None, Site.id.in_(site_ids_to_limit)))
        query = query.group_by(self.model.id)
        query = self._add_order_by(query, order_by, order_direction)

        total = query.count()

        return total, query.offset(skip).limit(limit).all()

    def filter(
        self,
        search: str | None,
        skip: int = static.DEFAULT_PAGINATION_SKIP,
        limit: int = static.DEFAULT_PAGINATION_LIMIT,
        order_by: Optional[str] = None,
        order_direction: Optional[str] = None,
        include_archived: bool = False,
    ) -> (int, List[Base]):
        """Get all items with applied filters,  skip (offset) and limits, sorted ascending by pk.

        :param search: search field by name or company_type
        :param skip: number of items to skip (offset)
        :param limit: number of items to get per page
        :param order_by: field name to order by
        :param order_direction: direction clause to order by (asc or desc)
        :param include_archived: if True, include archived companies
        :return: tuple of total and items list
        """
        query = self.db_session.query(self.model)
        if not include_archived:
            query = query.filter(self.model.is_archived == False)
        if search is not None:
            found_types = [company_type for company_type in CompanyTypes if search.lower() in company_type.value.lower()]
            search_company_types = [CompanyTypes(company_type) for company_type in found_types]
            query = query.filter(or_(Company.company_type.in_(search_company_types), Company.name.ilike(f"%{search}%")))
        query = self._add_order_by(query, order_by, order_direction)
        total = query.count()
        return total, query.offset(skip).limit(limit).all()

    def get_with_total_sites(self, target_id, site_ids_to_limit: Optional[list] = None):
        """Get company by id with total sites info."""

        query = self.db_session.query(  # noqa: ECE001
            self.model.id,
            self.model.name,
            self.model.address,
            self.model.phone,
            self.model.email,
            self.model.company_type,
            func.count(Site.id).label("total_sites"),
            func.count(
                case(
                    (SiteAdditionalFieldList.status.in_([SiteStatuses.placed_in_service.name]), 1),
                )
            ).label("sites_placed_in_service"),
            func.count(
                case(
                    (SiteAdditionalFieldList.status.in_([SiteStatuses.construction.name]), 1),
                )
            ).label("sites_under_construction"),
            func.count(
                case(
                    (SiteAdditionalFieldList.status.in_([SiteStatuses.decommissioned.name]), 1),
                )
            ).label("sites_decommissioned"),
            func.count(
                case(
                    (SiteAdditionalFieldList.status.in_([SiteStatuses.sold.name]), 1),
                )
            ).label("sites_sold"),
            # sum only sites in status `Placed in Service`
            self._build_system_size_clause(Site.system_size_ac).label("total_capacity"),
        )
        query = query.join(Site, and_(self.model.id == Site.company_id, Site.is_archived == False), isouter=True).join(
            SiteAdditionalFieldList, SiteAdditionalFieldList.site_id == Site.id, isouter=True
        )
        if site_ids_to_limit:
            query = query.filter(or_(Site.id == None, Site.id.in_(site_ids_to_limit)))
        query = query.group_by(self.model.id)
        query = query.filter(self.model.id == target_id)
        return query.one_or_none()

    def get_by_name(self, name):
        """Get company by its name."""
        return self.db_session.query(self.model).filter_by(name=name).first()

    def get_company_with_sites_overview(self, target_id, site_ids_to_limit: Optional[list]):
        query = self.db_session.query(
            self.model.id,
            self.model.name,
            func.count(Site.id).label("total_sites"),
            # calculate only for sites with status `Placed in Service`
            self._build_system_size_clause(Site.system_size_ac).label("total_system_size_ac"),
            self._build_system_size_clause(Site.system_size_dc).label("total_system_size_dc"),
        )
        query = query.outerjoin(Site, and_(self.model.id == Site.company_id, Site.is_archived == False)).join(
            SiteAdditionalFieldList, SiteAdditionalFieldList.site_id == Site.id, isouter=True
        )
        if site_ids_to_limit:
            query = query.filter(or_(Site.id == None, Site.id.in_(site_ids_to_limit)))
        query = query.filter(self.model.id == target_id)
        query = query.group_by(self.model.id)
        return query.one_or_none()

    def get_companies_general_info(
        self,
        company_ids: List[int] | None = None,
        skip: int = static.DEFAULT_PAGINATION_SKIP,
        limit: int = static.DEFAULT_PAGINATION_LIMIT,
        order_by: Optional[str] = None,
        order_direction: Optional[str] = None,
        search_filter: Filter | None = None,
    ):
        """Get companies IDs and names, with sorting and filtering.

        :param company_ids: list of user company IDs
        :param skip: number of items to skip (offset)
        :param limit: number of items to get per page
        :param order_by: field name to order by
        :param order_direction: direction clause to order by (asc or desc)
        :param search_filter: search value
        :return: tuple of total and items list
        """
        # we need to define default values explicitly, since they came as NULL because of validate_query_params
        order_by = order_by or CompaniesOrderByFieldEnum.name.value
        order_direction = order_direction or OrderDirectionEnum.asc.value
        query = self.db_session.query(
            self.model.id.label("id"),
            self.model.name.label("name"),
        )
        query = query.filter(self.model.is_archived == False)
        if company_ids is not None:
            query = query.filter(self.model.id.in_(company_ids))
        if search_filter:
            query = search_filter.filter(query)
        query = self._add_order_by(query, order_by, order_direction)

        total = query.count()

        return total, query.offset(skip).limit(limit).all()

    def get_filtered_with_sites(
        self,
        company_ids: List[int] | None = None,
        site_ids: List[int] | None = None,
        skip_pagination: bool = False,
    ):
        """Get companies with nested sites, filtered by accessible company/site IDs.
        
        This method is used for the user creation screen and ensures results are
        scoped to the user's accessible entities. BOTH companies AND nested sites
        are filtered to prevent data leakage.
        
        Args:
            company_ids: List of accessible company IDs (None = no company-level access)
            site_ids: List of accessible site IDs (None = no site-level access)
            skip_pagination: If True, return all results without pagination
            
        Returns:
            List of company dicts with their sites, filtered to accessible entities
        """
        if company_ids is None and site_ids is None:
            return []
        
        if company_ids is None:
            company_ids = []
        if site_ids is None:
            site_ids = []
        
        accessible_company_ids = set(company_ids)
        
        if site_ids:
            site_company_ids = self.db_session.query(Site.company_id).filter(
                Site.id.in_(site_ids)
            ).distinct().all()
            for (cid,) in site_company_ids:
                accessible_company_ids.add(cid)
        
        if not accessible_company_ids:
            return []
        
        companies = self.db_session.query(self.model).filter(
            self.model.id.in_(accessible_company_ids),
            self.model.is_archived == False,
        ).order_by(self.model.name).all()
        
        result = []
        for company in companies:
            company_dict = {
                "id": company.id,
                "name": company.name,
                "company_type": company.company_type.value if company.company_type else None,
                "sites": []
            }
            
            if company.id in company_ids:
                company_dict["sites"] = [
                    {"id": s.id, "name": s.name, "company_id": s.company_id}
                    for s in company.sites if not s.is_archived
                ]
            else:
                company_dict["sites"] = [
                    {"id": s.id, "name": s.name, "company_id": s.company_id}
                    for s in company.sites if s.id in site_ids and not s.is_archived
                ]
            
            if company.id in company_ids or company_dict["sites"]:
                result.append(company_dict)
        
        return result

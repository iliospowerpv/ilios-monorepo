from typing import Optional, Set

from sqlalchemy import String, asc, case, cast, desc, func

from app import static
from app.crud.base_crud import BaseCRUD
from app.models.alert import Alert, AlertSeverity
from app.models.board import BoardStatus
from app.models.company import Company
from app.models.device import Device
from app.models.site import Site
from app.models.task import Task
from app.schema.alert import CompanyAlertsOrderByFieldEnum


class AlertCRUD(BaseCRUD):
    """CRUD operations on Alert model."""

    def __init__(self, db_session):
        super().__init__(model=Alert, db_session=db_session)

    def _add_order_by_priority(self, query, order_direction):
        """Order alerts by severity priority critical, warning, informational and alert_start -
        DESC = newest first, ASC = oldest first"""
        order_direction_clause = desc if order_direction == "desc" else asc
        return query.order_by(
            # the most severe - custom filter on the severity level
            case(
                (self.model.severity == AlertSeverity.critical, 1),
                (self.model.severity == AlertSeverity.warning, 2),
                (self.model.severity == AlertSeverity.informational, 3),
                else_=4,
            ),
            # the most recent/older as a secondary sorting
            order_direction_clause(self.model.alert_start),
        )

    def _add_order_by_severity(self, query, order_direction):
        """Order alerts by severity priority:
        ASC = critical, warning, informational
        DESC = informational, warning, critical
        For multiple severities newest always first"""
        desc_case = case(
            (self.model.severity == AlertSeverity.critical, 3),
            (self.model.severity == AlertSeverity.warning, 2),
            (self.model.severity == AlertSeverity.informational, 1),
            else_=4,
        )
        asc_case = case(
            (self.model.severity == AlertSeverity.critical, 1),
            (self.model.severity == AlertSeverity.warning, 2),
            (self.model.severity == AlertSeverity.informational, 3),
            else_=4,
        )
        order_case = desc_case if order_direction == "desc" else asc_case
        return query.order_by(
            order_case,
            # secondary newest first
            desc(self.model.alert_start),
        )

    def get_by_target_entity_id(  # noqa CFQ002
        self,
        device_id: int | None = None,
        site_id: int | None = None,
        company_id: int | None = None,
        is_resolved: bool | None = None,
        skip: int = static.DEFAULT_PAGINATION_SKIP,
        limit: int = static.DEFAULT_PAGINATION_LIMIT,
        order_by: str | None = None,
        order_direction: str | None = None,
        site_ids_to_limit: list | None = None,
    ):
        expected_fields = [getattr(self.model, attr) for attr in self.model.__table__.columns.keys()]
        expected_fields.append(Task)
        if site_id or company_id:
            expected_fields.append(Device.name.label("device_name"))
        if company_id:
            expected_fields.append(Site.name.label("site_name"))
            expected_fields.append(Site.id.label("site_id"))

        query = self.db_session.query(*expected_fields)
        query = self._add_joins(query, site_id, company_id)
        # fetch task info for alert
        query = query.outerjoin(Task, self.model.id == Task.alert_id)
        # project only sites user has access to
        if site_ids_to_limit:
            query = query.filter(Site.id.in_(site_ids_to_limit))
        query = self._add_filters(query, device_id, site_id, company_id)
        if is_resolved is not None:
            query = query.filter(self.model.is_resolved == is_resolved)

        if order_by:
            if order_by == CompanyAlertsOrderByFieldEnum.type:
                # use explicitly alerts model's type, otherwise alchemy will pick type from joined tables,
                # e.g. devices.type
                order_by = self.model.type
            if order_by == CompanyAlertsOrderByFieldEnum.severity:
                query = self._add_order_by_severity(query, order_direction)
            else:
                query = self._add_order_by(query, order_by, order_direction)
        else:
            # Default ordering by severity priority critical, warning, informational and alert_start - older first
            query = self._add_order_by_priority(query, "asc")
        total = query.count()
        return total, query.offset(skip).limit(limit).all()

    def _add_joins(self, query, site_id, company_id):
        """Add extra joins to the query in case of need"""
        if site_id:
            query = query.join(Device, self.model.device_id == Device.id).join(Site, Device.site_id == Site.id)
            if company_id:
                query = query.join(Company, Site.company_id == Company.id)
        if company_id and not site_id:
            query = (
                query.join(Device, self.model.device_id == Device.id)
                .join(Site, Device.site_id == Site.id)
                .join(Company, Site.company_id == Company.id)
            )
        return query

    def _add_filters(self, query, device_id=None, site_id=None, company_id=None):
        """Add extra filters to the query in case of presence"""
        if company_id:
            query = query.filter(Company.id == company_id)
        if site_id:
            query = query.filter(Site.id == site_id)
        if device_id:
            query = query.filter(self.model.device_id == device_id)
        return query

    @staticmethod
    def _join_to_company_level(query):
        """Build join statement from Alerts to Company tables"""
        return query.join(Device).join(Site).join(Company)

    def _filter_unresolved(self, query):
        """Build filter statement to include only not resolved alerts"""
        return query.filter(self.model.is_resolved.is_(False))

    def get_company_alerts_overview(self, companies_ids: Set[int], site_ids_to_limit: Optional[list]):
        """Retrieve alerts for specific company(-ies)"""
        query = self.db_session.query(
            Company.id.label("company_id"),
            func.count().label("total"),
            func.string_agg(cast(self.model.severity, String).distinct(), ", ").label("severity"),
        )
        query = self._join_to_company_level(query)
        query = query.filter(Company.id.in_(companies_ids))
        if site_ids_to_limit:
            query = query.filter(Site.id.in_(site_ids_to_limit))
        query = self._filter_unresolved(query)
        query = query.group_by(Company.id).order_by(Company.id)
        return query.all()

    def get_company_most_critical_alerts(
        self, company_id, site_ids_to_limit: Optional[list], limit=static.OM_COMPANY_DASHBOARD_TOP_NUMBER
    ):
        """Retrieve most severe/recent alerts"""
        query = self.db_session.query(self.model.id, self.model.severity, self.model.alert_start, self.model.type)
        query = self._join_to_company_level(query)
        query = self._add_filters(query, company_id=company_id)
        if site_ids_to_limit:
            query = query.filter(Site.id.in_(site_ids_to_limit))
        query = self._filter_unresolved(query)
        query = self._add_order_by_priority(query, "desc").limit(limit)
        return query.all()

    def get_company_alerts_stats_with_tasks(self, company_id, site_ids_to_limit: Optional[list]):
        """Retrieve total stats about alerts and attached tasks"""
        query = self.db_session.query(
            self.model.severity,
            func.count().label("total"),
            # calculate total number of not completed tasks
            func.count(
                case(
                    (BoardStatus.name.not_in(["Cancelled", "Closed"]), 1),
                )
            ).label("unaccomplished_tasks_count"),
        )
        query = self._join_to_company_level(query)
        query = self._add_filters(query, company_id=company_id)
        if site_ids_to_limit:
            query = query.filter(Site.id.in_(site_ids_to_limit))
        # join statuses with left outer join, to ensure we calculate alerts even if they're not linked to the tasks
        query = query.join(Task, self.model.id == Task.alert_id, isouter=True).join(
            BoardStatus, BoardStatus.id == Task.status_id, isouter=True
        )
        query = self._filter_unresolved(query)
        query = query.group_by(self.model.severity)

        return query.all()

    def get_critical_devices_alerts_stats(self, device_ids):
        """Retrieve total critical alerts per device category"""
        query = self.db_session.query(self.model.severity, Device.category, func.count().label("total"))
        query = query.join(Device)
        query = query.filter(self.model.device_id.in_(device_ids))
        query = query.filter(self.model.severity == AlertSeverity.critical)
        query = self._filter_unresolved(query)
        query = query.group_by(Device.category, self.model.severity)

        return query.all()

    def get_site_alerts_overview(self, sites_ids: Set[int]):
        """Retrieve alerts for specific site(-es)"""
        query = self.db_session.query(
            Site.id.label("site_id"),
            func.count().label("total"),
            func.string_agg(cast(self.model.severity, String).distinct(), ", ").label("severity"),
        )
        query = query.join(Device, Device.id == self.model.device_id).join(Site)
        query = query.filter(Site.id.in_(sites_ids))
        query = self._filter_unresolved(query)
        query = query.group_by(Site.id).order_by(Site.id)
        return query.all()

    def get_device_alerts_overview(self, devices_ids: Set[int]):
        """Retrieve alerts for specific device(-es)"""
        query = self.db_session.query(
            Device.id.label("device_id"),
            func.count().label("total"),
            func.string_agg(cast(self.model.severity, String).distinct(), ", ").label("severity"),
        )
        query = query.join(Device)
        query = query.filter(Device.id.in_(devices_ids))
        query = self._filter_unresolved(query)
        query = query.group_by(Device.id).order_by(Device.id)
        return query.all()

    def get_by_external_id(self, device_id: int, external_id: str):
        query = self.db_session.query(self.model).filter(
            self.model.device_id == device_id, self.model.external_id == external_id
        )
        return query.one_or_none()

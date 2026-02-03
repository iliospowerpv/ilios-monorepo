"""Finance module CRUD operations."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.finance import (
    FinanceActual,
    FinanceApproval,
    FinanceBudget,
    FinanceBudgetLineItem,
    FinanceObligation,
    FinanceVendor,
)
from app.models.site import Site
from app.models.user import User
from app.static.finance import FinanceBudgetStatus, FinanceObligationStatus


class FinanceVendorCRUD:
    @staticmethod
    def get_by_id(db: Session, vendor_id: int) -> Optional[FinanceVendor]:
        return db.query(FinanceVendor).filter(FinanceVendor.id == vendor_id).first()

    @staticmethod
    def get_all(
        db: Session,
        company_id: int,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
    ) -> tuple[list[FinanceVendor], int]:
        query = db.query(FinanceVendor).filter(FinanceVendor.company_id == company_id)
        if is_active is not None:
            query = query.filter(FinanceVendor.is_active == is_active)
        total = query.count()
        items = query.order_by(FinanceVendor.name).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def create(db: Session, company_id: int, data: dict) -> FinanceVendor:
        vendor = FinanceVendor(company_id=company_id, **data)
        db.add(vendor)
        db.commit()
        db.refresh(vendor)
        return vendor

    @staticmethod
    def update(db: Session, vendor: FinanceVendor, data: dict) -> FinanceVendor:
        for key, value in data.items():
            if value is not None:
                setattr(vendor, key, value)
        vendor.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(vendor)
        return vendor

    @staticmethod
    def delete(db: Session, vendor: FinanceVendor) -> None:
        db.delete(vendor)
        db.commit()


class FinanceBudgetCRUD:
    @staticmethod
    def get_by_id(db: Session, budget_id: int) -> Optional[FinanceBudget]:
        return (
            db.query(FinanceBudget)
            .options(joinedload(FinanceBudget.line_items).joinedload(FinanceBudgetLineItem.vendor))
            .options(joinedload(FinanceBudget.site))
            .filter(FinanceBudget.id == budget_id)
            .first()
        )

    @staticmethod
    def get_all(
        db: Session,
        company_id: int,
        site_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        status: Optional[FinanceBudgetStatus] = None,
    ) -> tuple[list[FinanceBudget], int]:
        query = db.query(FinanceBudget).filter(FinanceBudget.company_id == company_id)
        if site_id is not None:
            query = query.filter(FinanceBudget.site_id == site_id)
        if status is not None:
            query = query.filter(FinanceBudget.status == status)
        total = query.count()
        items = query.order_by(FinanceBudget.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def create(db: Session, company_id: int, user_id: int, data: dict) -> FinanceBudget:
        line_items_data = data.pop("line_items", None) or []
        budget = FinanceBudget(company_id=company_id, created_by_id=user_id, **data)
        db.add(budget)
        db.flush()
        for item_data in line_items_data:
            line_item = FinanceBudgetLineItem(budget_id=budget.id, **item_data)
            db.add(line_item)
        db.commit()
        db.refresh(budget)
        return budget

    @staticmethod
    def update(db: Session, budget: FinanceBudget, data: dict) -> FinanceBudget:
        for key, value in data.items():
            if value is not None:
                setattr(budget, key, value)
        budget.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(budget)
        return budget

    @staticmethod
    def delete(db: Session, budget: FinanceBudget) -> None:
        db.delete(budget)
        db.commit()

    @staticmethod
    def get_budget_totals(db: Session, budget_id: int) -> dict:
        result = (
            db.query(
                func.coalesce(func.sum(FinanceBudgetLineItem.amount_planned), 0).label("total_planned"),
                func.coalesce(func.sum(FinanceBudgetLineItem.amount_authorized), 0).label("total_authorized"),
                func.coalesce(func.sum(FinanceBudgetLineItem.amount_actual), 0).label("total_actual"),
            )
            .filter(FinanceBudgetLineItem.budget_id == budget_id)
            .first()
        )
        total_planned = float(result.total_planned) if result else 0.0
        total_authorized = float(result.total_authorized) if result else 0.0
        total_actual = float(result.total_actual) if result else 0.0
        return {
            "total_planned": total_planned,
            "total_authorized": total_authorized,
            "total_actual": total_actual,
            "variance": total_planned - total_actual,
        }

    @staticmethod
    def submit(db: Session, budget: FinanceBudget) -> FinanceBudget:
        budget.status = FinanceBudgetStatus.submitted
        budget.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(budget)
        return budget


class FinanceBudgetLineItemCRUD:
    @staticmethod
    def get_by_id(db: Session, item_id: int) -> Optional[FinanceBudgetLineItem]:
        return db.query(FinanceBudgetLineItem).filter(FinanceBudgetLineItem.id == item_id).first()

    @staticmethod
    def create(db: Session, budget_id: int, data: dict) -> FinanceBudgetLineItem:
        item = FinanceBudgetLineItem(budget_id=budget_id, **data)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def update(db: Session, item: FinanceBudgetLineItem, data: dict) -> FinanceBudgetLineItem:
        for key, value in data.items():
            if value is not None:
                setattr(item, key, value)
        item.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def delete(db: Session, item: FinanceBudgetLineItem) -> None:
        db.delete(item)
        db.commit()


class FinanceObligationCRUD:
    @staticmethod
    def get_by_id(db: Session, obligation_id: int) -> Optional[FinanceObligation]:
        return (
            db.query(FinanceObligation)
            .options(joinedload(FinanceObligation.vendor))
            .options(joinedload(FinanceObligation.site))
            .options(joinedload(FinanceObligation.approvals).joinedload(FinanceApproval.approved_by))
            .filter(FinanceObligation.id == obligation_id)
            .first()
        )

    @staticmethod
    def get_all(
        db: Session,
        company_id: int,
        site_id: Optional[int] = None,
        status: Optional[FinanceObligationStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[FinanceObligation], int]:
        query = (
            db.query(FinanceObligation)
            .options(joinedload(FinanceObligation.vendor))
            .options(joinedload(FinanceObligation.site))
            .filter(FinanceObligation.company_id == company_id)
        )
        if site_id is not None:
            query = query.filter(FinanceObligation.site_id == site_id)
        if status is not None:
            query = query.filter(FinanceObligation.status == status)
        total = query.count()
        items = query.order_by(FinanceObligation.requested_date.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def create(db: Session, company_id: int, user_id: int, data: dict) -> FinanceObligation:
        obligation = FinanceObligation(
            company_id=company_id,
            created_by_id=user_id,
            status=FinanceObligationStatus.draft,
            **data,
        )
        db.add(obligation)
        db.commit()
        db.refresh(obligation)
        return obligation

    @staticmethod
    def update(db: Session, obligation: FinanceObligation, data: dict) -> FinanceObligation:
        for key, value in data.items():
            if value is not None:
                setattr(obligation, key, value)
        obligation.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obligation)
        return obligation

    @staticmethod
    def submit(db: Session, obligation: FinanceObligation, prerequisite_snapshot: dict) -> FinanceObligation:
        obligation.status = FinanceObligationStatus.submitted
        obligation.prerequisite_snapshot = prerequisite_snapshot
        obligation.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obligation)
        return obligation

    @staticmethod
    def delete(db: Session, obligation: FinanceObligation) -> None:
        db.delete(obligation)
        db.commit()

    @staticmethod
    def get_pending_by_site(db: Session, site_id: int) -> tuple[int, float]:
        result = (
            db.query(
                func.count(FinanceObligation.id).label("count"),
                func.coalesce(func.sum(FinanceObligation.amount_requested), 0).label("total"),
            )
            .filter(
                FinanceObligation.site_id == site_id,
                FinanceObligation.status == FinanceObligationStatus.submitted,
            )
            .first()
        )
        return (result.count or 0, float(result.total or 0))


class FinanceApprovalCRUD:
    @staticmethod
    def create_for_obligation(db: Session, obligation_id: int, user_id: int, data: dict) -> FinanceApproval:
        approval = FinanceApproval(
            obligation_id=obligation_id,
            approved_by_id=user_id,
            **data,
        )
        db.add(approval)
        obligation = db.query(FinanceObligation).filter(FinanceObligation.id == obligation_id).first()
        if obligation:
            if data["decision"].value == "approved" or data["decision"].value == "override":
                obligation.status = FinanceObligationStatus.approved
            elif data["decision"].value == "rejected":
                obligation.status = FinanceObligationStatus.rejected
            obligation.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(approval)
        return approval

    @staticmethod
    def create_for_budget(db: Session, budget_id: int, user_id: int, data: dict) -> FinanceApproval:
        approval = FinanceApproval(
            budget_id=budget_id,
            approved_by_id=user_id,
            **data,
        )
        db.add(approval)
        budget = db.query(FinanceBudget).filter(FinanceBudget.id == budget_id).first()
        if budget:
            if data["decision"].value == "approved" or data["decision"].value == "override":
                budget.status = FinanceBudgetStatus.approved
            elif data["decision"].value == "rejected":
                budget.status = FinanceBudgetStatus.rejected
            budget.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(approval)
        return approval

    @staticmethod
    def create(db: Session, obligation_id: int, user_id: int, data: dict) -> FinanceApproval:
        return FinanceApprovalCRUD.create_for_obligation(db, obligation_id, user_id, data)

    @staticmethod
    def get_by_obligation(db: Session, obligation_id: int) -> list[FinanceApproval]:
        return (
            db.query(FinanceApproval)
            .options(joinedload(FinanceApproval.approved_by))
            .filter(FinanceApproval.obligation_id == obligation_id)
            .order_by(FinanceApproval.approved_at.desc())
            .all()
        )

    @staticmethod
    def get_by_budget(db: Session, budget_id: int) -> list[FinanceApproval]:
        return (
            db.query(FinanceApproval)
            .options(joinedload(FinanceApproval.approved_by))
            .filter(FinanceApproval.budget_id == budget_id)
            .order_by(FinanceApproval.approved_at.desc())
            .all()
        )


class FinanceActualCRUD:
    @staticmethod
    def get_by_id(db: Session, actual_id: int) -> Optional[FinanceActual]:
        return db.query(FinanceActual).filter(FinanceActual.id == actual_id).first()

    @staticmethod
    def get_all(
        db: Session,
        company_id: int,
        site_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[FinanceActual], int]:
        query = (
            db.query(FinanceActual)
            .options(joinedload(FinanceActual.vendor))
            .options(joinedload(FinanceActual.site))
            .filter(FinanceActual.company_id == company_id)
        )
        if site_id is not None:
            query = query.filter(FinanceActual.site_id == site_id)
        total = query.count()
        items = query.order_by(FinanceActual.transaction_date.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def create(db: Session, company_id: int, user_id: int, data: dict) -> FinanceActual:
        actual = FinanceActual(company_id=company_id, created_by_id=user_id, **data)
        db.add(actual)
        db.commit()
        db.refresh(actual)
        return actual

    @staticmethod
    def update(db: Session, actual: FinanceActual, data: dict) -> FinanceActual:
        for key, value in data.items():
            if value is not None:
                setattr(actual, key, value)
        actual.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(actual)
        return actual

    @staticmethod
    def delete(db: Session, actual: FinanceActual) -> None:
        db.delete(actual)
        db.commit()

    @staticmethod
    def get_totals_by_site(db: Session, site_id: int) -> float:
        result = (
            db.query(func.coalesce(func.sum(FinanceActual.amount), 0).label("total"))
            .filter(FinanceActual.site_id == site_id)
            .scalar()
        )
        return float(result or 0)


class FinancePortfolioCRUD:
    @staticmethod
    def get_site_summary(db: Session, site: Site) -> dict:
        budgets = db.query(FinanceBudget).filter(FinanceBudget.site_id == site.id).all()
        total_planned = 0.0
        total_authorized = 0.0
        total_actual = 0.0
        for budget in budgets:
            totals = FinanceBudgetCRUD.get_budget_totals(db, budget.id)
            total_planned += totals["total_planned"]
            total_authorized += totals["total_authorized"]
            total_actual += totals["total_actual"]
        pending_count, pending_amount = FinanceObligationCRUD.get_pending_by_site(db, site.id)
        actuals_total = FinanceActualCRUD.get_totals_by_site(db, site.id)
        total_actual = max(total_actual, actuals_total)
        missing_prerequisites = FinancePortfolioCRUD.get_missing_prerequisites(site)
        return {
            "site_id": site.id,
            "site_name": site.name,
            "total_budget_planned": total_planned,
            "total_budget_authorized": total_authorized,
            "total_budget_actual": total_actual,
            "budget_variance": total_planned - total_actual,
            "pending_obligations": pending_count,
            "pending_obligations_amount": pending_amount,
            "finance_ready": len(missing_prerequisites) == 0,
            "missing_prerequisites": missing_prerequisites,
        }

    @staticmethod
    def get_missing_prerequisites(site: Site) -> list[str]:
        missing = []
        if not hasattr(site, "site_additional_field_list") or not site.site_additional_field_list:
            missing.append("Site additional fields not configured")
            return missing
        fields = site.site_additional_field_list
        if not getattr(fields, "ownership_structure", None):
            missing.append("Ownership Structure")
        if not getattr(fields, "interconnection_utility", None):
            missing.append("Interconnection Utility")
        if not getattr(fields, "insurance_provider", None):
            missing.append("Insurance Provider")
        if not getattr(fields, "key_date_pto", None):
            missing.append("PTO Date")
        if not getattr(fields, "key_date_cod", None):
            missing.append("COD Date")
        return missing[:3]

    @staticmethod
    def get_portfolio_summary(db: Session, company_id: int) -> dict:
        sites = db.query(Site).filter(Site.company_id == company_id).all()
        site_summaries = []
        total_planned = 0.0
        total_authorized = 0.0
        total_actual = 0.0
        sites_ready = 0
        sites_not_ready = 0
        total_pending = 0
        total_pending_amount = 0.0
        for site in sites:
            summary = FinancePortfolioCRUD.get_site_summary(db, site)
            site_summaries.append(summary)
            total_planned += summary["total_budget_planned"]
            total_authorized += summary["total_budget_authorized"]
            total_actual += summary["total_budget_actual"]
            total_pending += summary["pending_obligations"]
            total_pending_amount += summary["pending_obligations_amount"]
            if summary["finance_ready"]:
                sites_ready += 1
            else:
                sites_not_ready += 1
        return {
            "summary": {
                "total_budget_planned": total_planned,
                "total_budget_authorized": total_authorized,
                "total_budget_actual": total_actual,
                "total_variance": total_planned - total_actual,
                "sites_finance_ready": sites_ready,
                "sites_not_ready": sites_not_ready,
                "total_pending_obligations": total_pending,
                "total_pending_amount": total_pending_amount,
            },
            "sites": site_summaries,
        }

"""Seed a demo deal for Solara Industrial Energy in MIPA Negotiating stage.

Idempotent: skips if a deal with the same name already exists for the company.

Run from backend/ilios-server:
    python -m scripts.seed_demo_deal
"""
from datetime import date, timedelta
from decimal import Decimal

from app.main import app as _app  # noqa: F401  ensures all models register
from app.db.session import SessionFactory
from app.models.sales import Deal, SalesStateTransition

DEMO_COMPANY_ID = 15
DEMO_DEAL_NAME = "Sunridge Logistics Park"


def seed():
    db = SessionFactory()
    try:
        existing = (
            db.query(Deal)
            .filter(Deal.company_id == DEMO_COMPANY_ID, Deal.name == DEMO_DEAL_NAME)
            .first()
        )
        if existing:
            print(f"[skip] Deal '{DEMO_DEAL_NAME}' already exists (id={existing.id})")
            return

        deal = Deal(
            name=DEMO_DEAL_NAME,
            developer_name="Vanguard Solar Developers, LLC",
            sales_stage="mipa_negotiating",
            lifecycle_state="sales_pre_diligence",
            quoted_by="Solara Origination Team",
            last_action="Final MIPA red-line returned to seller's counsel",
            next_action="Schedule MIPA execution call with seller principals",
            next_action_status="in_progress",
            next_action_date=date.today() + timedelta(days=10),
            ownership_structure="LLC - Single Asset SPV",
            sales_notes=(
                "Tier-1 developer, repeat counterparty. MIPA in final red-line; "
                "key open points: indemnity cap and PTO milestone definition. "
                "Targeting MIPA execution within 2 weeks, COD Q4 2026."
            ),
            address="4820 Industrial Parkway",
            city="Bakersfield",
            state="CA",
            zip_code="93308",
            county="Kern",
            latitude=Decimal("35.4137"),
            longitude=Decimal("-119.0187"),
            project_company="Sunridge Logistics Solar SPV, LLC",
            mipa_per_watt=Decimal("0.2850"),
            offtaker_name="Sunridge Logistics Holdings",
            offtaker_legal_name="Sunridge Logistics Holdings, LLC",
            utility_rate="PG&E B-19",
            utility_zone="PG&E - Central Valley",
            system_size_ac=Decimal("18500.00"),
            system_size_dc=Decimal("24500.00"),
            itc_percent=Decimal("40.00"),
            pipeline_value=Decimal("6982500.00"),
            probability=75,
            target_close_date=date.today() + timedelta(days=45),
            company_id=DEMO_COMPANY_ID,
            assigned_owner_id=1,
            is_converted=False,
        )
        db.add(deal)
        db.flush()

        db.add(
            SalesStateTransition(
                deal_id=deal.id,
                transition_type="deal_created",
                from_state=None,
                to_state="mipa_negotiating",
                notes="Demo seed",
                changed_by_id=1,
            )
        )
        db.commit()
        print(f"[ok] Created demo deal '{DEMO_DEAL_NAME}' (id={deal.id}) in MIPA Negotiating")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

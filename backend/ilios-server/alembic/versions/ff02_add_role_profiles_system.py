"""Add role profiles system for deep stakeholder role definitions

Revision ID: ff02_add_role_profiles
Revises: ff01_add_budget_approval_support
Create Date: 2026-02-03

This migration adds:
1. role_profiles table for defining granular role permissions
2. New columns on user_company_access for role profile assignment
3. Seed data for initial 15 role profiles

This preserves the new Portfolio → Company → Project hierarchy while
adding deep role definitions without resurrecting the legacy 45-role system.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY


revision: str = "ff02_add_role_profiles"
down_revision: Union[str, None] = "ff01_budget_approval"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INITIAL_PROFILES = [
    {
        "key": "company_admin",
        "label": "Company Admin",
        "description": "Full administrative access including user management and settings",
        "applicable_company_types": None,
        "default_module_permissions": {
            "assets_management": {"view": True, "edit": True},
            "diligence": {"view": True, "edit": True},
            "operation_maintenance": {"view": True, "edit": True},
            "finance": {"view": True, "edit": True},
            "settings": {"view": True, "edit": True},
            "reporting": {"view": True, "edit": True}
        },
        "default_dashboard_key": "default",
        "display_order": 1
    },
    {
        "key": "executive",
        "label": "Executive",
        "description": "Executive overview access across all modules",
        "applicable_company_types": ["project_site_owner"],
        "default_module_permissions": {
            "assets_management": {"view": True, "edit": True},
            "diligence": {"view": True, "edit": True},
            "operation_maintenance": {"view": True, "edit": True},
            "finance": {"view": True, "edit": False},
            "reporting": {"view": True, "edit": True}
        },
        "default_dashboard_key": "default",
        "display_order": 2
    },
    {
        "key": "asset_manager",
        "label": "Asset Manager",
        "description": "Manages asset portfolio, operations, and due diligence",
        "applicable_company_types": ["project_site_owner"],
        "default_module_permissions": {
            "assets_management": {"view": True, "edit": True},
            "diligence": {"view": True, "edit": True},
            "operation_maintenance": {"view": True, "edit": True},
            "reporting": {"view": True, "edit": True}
        },
        "default_dashboard_key": "default",
        "display_order": 3
    },
    {
        "key": "operations_manager",
        "label": "Operations Manager",
        "description": "Manages O&M activities and asset operations",
        "applicable_company_types": ["project_site_owner", "operation_maintenance_contractor"],
        "default_module_permissions": {
            "assets_management": {"view": True, "edit": True},
            "diligence": {"view": True, "edit": True},
            "operation_maintenance": {"view": True, "edit": True},
            "reporting": {"view": True, "edit": True}
        },
        "default_dashboard_key": "default",
        "display_order": 4
    },
    {
        "key": "diligence_manager",
        "label": "Diligence Manager",
        "description": "Manages due diligence workflows and documentation",
        "applicable_company_types": ["project_site_owner"],
        "default_module_permissions": {
            "assets_management": {"view": True, "edit": True},
            "diligence": {"view": True, "edit": True},
            "reporting": {"view": True, "edit": True}
        },
        "default_dashboard_key": "default",
        "display_order": 5
    },
    {
        "key": "finance_specialist",
        "label": "Finance Specialist",
        "description": "Manages financial tracking, budgets, and obligations",
        "applicable_company_types": ["project_site_owner"],
        "default_module_permissions": {
            "diligence": {"view": True, "edit": True},
            "finance": {"view": True, "edit": True},
            "reporting": {"view": True, "edit": True}
        },
        "default_dashboard_key": "default",
        "display_order": 6
    },
    {
        "key": "legal_specialist",
        "label": "Legal Specialist",
        "description": "Manages legal documentation and compliance",
        "applicable_company_types": ["project_site_owner"],
        "default_module_permissions": {
            "diligence": {"view": True, "edit": True},
            "reporting": {"view": True, "edit": True}
        },
        "default_dashboard_key": "default",
        "display_order": 7
    },
    {
        "key": "project_manager",
        "label": "Project Manager",
        "description": "Manages project execution and coordination",
        "applicable_company_types": ["project_site_owner", "operation_maintenance_contractor"],
        "default_module_permissions": {
            "assets_management": {"view": True, "edit": True},
            "diligence": {"view": True, "edit": True},
            "operation_maintenance": {"view": True, "edit": True},
            "reporting": {"view": True, "edit": True}
        },
        "default_dashboard_key": "default",
        "display_order": 8
    },
    {
        "key": "field_technician",
        "label": "Field Technician",
        "description": "Field operations and maintenance technician",
        "applicable_company_types": ["operation_maintenance_contractor"],
        "default_module_permissions": {
            "assets_management": {"view": True, "edit": True},
            "operation_maintenance": {"view": True, "edit": True},
            "diligence": {"view": True, "edit": True}
        },
        "default_dashboard_key": "role_based",
        "display_order": 9
    },
    {
        "key": "investor",
        "label": "Investor",
        "description": "Investment portfolio view and reporting",
        "applicable_company_types": ["investor"],
        "default_module_permissions": {
            "investor_dashboard": {"view": True, "edit": True},
            "reporting": {"view": True, "edit": True}
        },
        "default_dashboard_key": "investor",
        "display_order": 10
    },
    {
        "key": "lender_construction",
        "label": "Lender - Construction",
        "description": "Construction lender with diligence access",
        "applicable_company_types": ["bank"],
        "default_module_permissions": {
            "role_based_dashboard": {"view": True, "edit": True},
            "diligence": {"view": True, "edit": True},
            "reporting": {"view": True, "edit": True}
        },
        "default_dashboard_key": "role_based",
        "display_order": 11
    },
    {
        "key": "lender_perm_debt",
        "label": "Lender - Permanent Debt",
        "description": "Permanent debt lender with diligence access",
        "applicable_company_types": ["bank"],
        "default_module_permissions": {
            "role_based_dashboard": {"view": True, "edit": True},
            "diligence": {"view": True, "edit": True},
            "reporting": {"view": True, "edit": True}
        },
        "default_dashboard_key": "role_based",
        "display_order": 12
    },
    {
        "key": "appraiser",
        "label": "Appraiser",
        "description": "Property appraiser with diligence access",
        "applicable_company_types": ["appraiser"],
        "default_module_permissions": {
            "role_based_dashboard": {"view": True, "edit": True},
            "diligence": {"view": True, "edit": True},
            "reporting": {"view": True, "edit": True}
        },
        "default_dashboard_key": "role_based",
        "display_order": 13
    },
    {
        "key": "engineer",
        "label": "Engineer",
        "description": "Engineering consultant with technical access",
        "applicable_company_types": ["engineering_firm"],
        "default_module_permissions": {
            "role_based_dashboard": {"view": True, "edit": True},
            "diligence": {"view": True, "edit": True},
            "reporting": {"view": True, "edit": True}
        },
        "default_dashboard_key": "role_based",
        "display_order": 14
    },
    {
        "key": "insurance_agent",
        "label": "Insurance Agent",
        "description": "Insurance agent with asset and diligence access",
        "applicable_company_types": ["insurance_company"],
        "default_module_permissions": {
            "assets_management": {"view": True, "edit": True},
            "role_based_dashboard": {"view": True, "edit": True},
            "diligence": {"view": True, "edit": True},
            "reporting": {"view": True, "edit": True}
        },
        "default_dashboard_key": "role_based",
        "display_order": 15
    }
]


def upgrade() -> None:
    op.create_table(
        "role_profiles",
        sa.Column("key", sa.String(50), primary_key=True),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("applicable_company_types", ARRAY(sa.String), nullable=True),
        sa.Column("default_module_permissions", JSONB, nullable=False, server_default="{}"),
        sa.Column("default_dashboard_key", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0")
    )
    
    op.add_column(
        "user_company_access",
        sa.Column("role_profile_key", sa.String(50), nullable=True)
    )
    op.add_column(
        "user_company_access",
        sa.Column("module_permissions", JSONB, nullable=True)
    )
    op.add_column(
        "user_company_access",
        sa.Column("dashboard_key", sa.String(50), nullable=True)
    )
    
    op.create_foreign_key(
        "fk_user_company_access_role_profile",
        "user_company_access",
        "role_profiles",
        ["role_profile_key"],
        ["key"],
        ondelete="SET NULL"
    )
    
    op.create_index(
        "ix_user_company_access_role_profile_key",
        "user_company_access",
        ["role_profile_key"]
    )
    
    role_profiles_table = sa.table(
        "role_profiles",
        sa.column("key", sa.String),
        sa.column("label", sa.String),
        sa.column("description", sa.Text),
        sa.column("applicable_company_types", ARRAY(sa.String)),
        sa.column("default_module_permissions", JSONB),
        sa.column("default_dashboard_key", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("display_order", sa.Integer)
    )
    
    for profile in INITIAL_PROFILES:
        op.execute(
            role_profiles_table.insert().values(
                key=profile["key"],
                label=profile["label"],
                description=profile["description"],
                applicable_company_types=profile["applicable_company_types"],
                default_module_permissions=profile["default_module_permissions"],
                default_dashboard_key=profile["default_dashboard_key"],
                is_active=True,
                display_order=profile["display_order"]
            )
        )


def downgrade() -> None:
    op.drop_constraint(
        "fk_user_company_access_role_profile",
        "user_company_access",
        type_="foreignkey"
    )
    op.drop_index("ix_user_company_access_role_profile_key", table_name="user_company_access")
    op.drop_column("user_company_access", "dashboard_key")
    op.drop_column("user_company_access", "module_permissions")
    op.drop_column("user_company_access", "role_profile_key")
    op.drop_table("role_profiles")

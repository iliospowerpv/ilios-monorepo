"""Access Health Admin API - validation and repair utilities."""

import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.schema.user import CurrentUserSchema

access_health_router = APIRouter()
logger = logging.getLogger(__name__)


class ValidationIssue(BaseModel):
    issue_type: str
    table: str
    record_id: int
    details: str


class ValidationResult(BaseModel):
    check_name: str
    description: str
    passed: bool
    issue_count: int
    issues: List[ValidationIssue]


class RepairResult(BaseModel):
    repair_type: str
    records_fixed: int
    success: bool
    message: str


class AccessHealthResponse(BaseModel):
    validations: List[ValidationResult]
    overall_healthy: bool
    total_issues: int


@access_health_router.get(
    "",
    response_model=AccessHealthResponse,
    summary="Get access health validation results",
    description="Run validation checks on access model data integrity.",
)
async def get_access_health(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> AccessHealthResponse:
    """Run access health validation checks."""
    if not current_user.has_platform_bypass:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can view access health"
        )
    
    validations = []
    
    inv1_result = check_inv1_violations(db_session)
    validations.append(inv1_result)
    
    orphaned_result = check_orphaned_memberships(db_session)
    validations.append(orphaned_result)
    
    suspended_access_result = check_suspended_with_access(db_session)
    validations.append(suspended_access_result)
    
    duplicate_result = check_duplicate_memberships(db_session)
    validations.append(duplicate_result)
    
    total_issues = sum(v.issue_count for v in validations)
    overall_healthy = total_issues == 0
    
    return AccessHealthResponse(
        validations=validations,
        overall_healthy=overall_healthy,
        total_issues=total_issues
    )


def check_inv1_violations(db_session: Session) -> ValidationResult:
    """Check for INV-1 violations: UserProject.company_id must match sites.company_id."""
    query = text("""
        SELECT up.id, up.user_id, up.site_id, up.company_id, s.company_id as expected_company_id
        FROM user_projects up
        JOIN sites s ON up.site_id = s.id
        WHERE up.company_id IS NOT NULL AND up.company_id != s.company_id
    """)
    
    result = db_session.execute(query)
    rows = result.fetchall()
    
    issues = []
    for row in rows:
        issues.append(ValidationIssue(
            issue_type="INV-1",
            table="user_projects",
            record_id=row.id,
            details=f"user_project {row.id}: company_id={row.company_id} but site {row.site_id} belongs to company {row.expected_company_id}"
        ))
    
    return ValidationResult(
        check_name="INV-1 Integrity",
        description="UserProject.company_id must match sites.company_id for referenced site_id",
        passed=len(issues) == 0,
        issue_count=len(issues),
        issues=issues
    )


def check_orphaned_memberships(db_session: Session) -> ValidationResult:
    """Check for orphaned memberships (company_id or site_id references missing)."""
    issues = []
    
    orphaned_company_query = text("""
        SELECT uca.id, uca.user_id, uca.company_id
        FROM user_company_access uca
        LEFT JOIN companies c ON uca.company_id = c.id
        WHERE c.id IS NULL
    """)
    result = db_session.execute(orphaned_company_query)
    for row in result.fetchall():
        issues.append(ValidationIssue(
            issue_type="orphaned_company",
            table="user_company_access",
            record_id=row.id,
            details=f"user_company_access {row.id}: references non-existent company_id={row.company_id}"
        ))
    
    orphaned_project_query = text("""
        SELECT up.id, up.user_id, up.site_id
        FROM user_projects up
        LEFT JOIN sites s ON up.site_id = s.id
        WHERE s.id IS NULL
    """)
    result = db_session.execute(orphaned_project_query)
    for row in result.fetchall():
        issues.append(ValidationIssue(
            issue_type="orphaned_project",
            table="user_projects",
            record_id=row.id,
            details=f"user_projects {row.id}: references non-existent site_id={row.site_id}"
        ))
    
    return ValidationResult(
        check_name="Orphaned Memberships",
        description="Check for memberships referencing non-existent companies or projects",
        passed=len(issues) == 0,
        issue_count=len(issues),
        issues=issues
    )


def check_suspended_with_access(db_session: Session) -> ValidationResult:
    """Check for disabled/suspended users who might still appear with access."""
    query = text("""
        SELECT DISTINCT u.id, u.email, u.is_active
        FROM users u
        WHERE u.is_active = false
        AND (
            EXISTS (SELECT 1 FROM user_company_access uca WHERE uca.user_id = u.id AND uca.status = 'active')
            OR EXISTS (SELECT 1 FROM user_projects up WHERE up.user_id = u.id AND up.status = 'active')
            OR EXISTS (SELECT 1 FROM user_portfolio_access upa WHERE upa.user_id = u.id AND upa.status = 'active')
        )
    """)
    
    result = db_session.execute(query)
    rows = result.fetchall()
    
    issues = []
    for row in rows:
        issues.append(ValidationIssue(
            issue_type="inactive_user_active_membership",
            table="users",
            record_id=row.id,
            details=f"User {row.email} (id={row.id}) is inactive but has active memberships"
        ))
    
    return ValidationResult(
        check_name="Inactive Users with Active Memberships",
        description="Users marked as inactive should not have active memberships",
        passed=len(issues) == 0,
        issue_count=len(issues),
        issues=issues
    )


def check_duplicate_memberships(db_session: Session) -> ValidationResult:
    """Check for duplicate memberships (same user, same entity)."""
    issues = []
    
    dup_company_query = text("""
        SELECT user_id, company_id, COUNT(*) as cnt
        FROM user_company_access
        GROUP BY user_id, company_id
        HAVING COUNT(*) > 1
    """)
    result = db_session.execute(dup_company_query)
    for row in result.fetchall():
        issues.append(ValidationIssue(
            issue_type="duplicate_company_membership",
            table="user_company_access",
            record_id=row.user_id,
            details=f"User {row.user_id} has {row.cnt} memberships for company {row.company_id}"
        ))
    
    dup_project_query = text("""
        SELECT user_id, site_id, COUNT(*) as cnt
        FROM user_projects
        GROUP BY user_id, site_id
        HAVING COUNT(*) > 1
    """)
    result = db_session.execute(dup_project_query)
    for row in result.fetchall():
        issues.append(ValidationIssue(
            issue_type="duplicate_project_membership",
            table="user_projects",
            record_id=row.user_id,
            details=f"User {row.user_id} has {row.cnt} memberships for project {row.site_id}"
        ))
    
    return ValidationResult(
        check_name="Duplicate Memberships",
        description="Check for users with multiple memberships to the same entity",
        passed=len(issues) == 0,
        issue_count=len(issues),
        issues=issues
    )


@access_health_router.post(
    "/repair/orphaned",
    response_model=RepairResult,
    summary="Remove orphaned membership rows",
    description="Safely remove membership rows that reference non-existent entities.",
)
async def repair_orphaned_memberships(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> RepairResult:
    """Remove orphaned membership rows."""
    if not current_user.has_platform_bypass:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can perform repairs"
        )
    
    total_removed = 0
    
    delete_orphaned_company = text("""
        DELETE FROM user_company_access
        WHERE company_id NOT IN (SELECT id FROM companies)
    """)
    result = db_session.execute(delete_orphaned_company)
    total_removed += result.rowcount
    
    delete_orphaned_project = text("""
        DELETE FROM user_projects
        WHERE site_id NOT IN (SELECT id FROM sites)
    """)
    result = db_session.execute(delete_orphaned_project)
    total_removed += result.rowcount
    
    db_session.commit()
    
    return RepairResult(
        repair_type="orphaned_memberships",
        records_fixed=total_removed,
        success=True,
        message=f"Removed {total_removed} orphaned membership records"
    )


@access_health_router.post(
    "/repair/inv1",
    response_model=RepairResult,
    summary="Normalize INV-1 violations",
    description="Fix user_projects.company_id to match sites.company_id.",
)
async def repair_inv1_violations(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> RepairResult:
    """Fix INV-1 violations by setting correct company_id from sites."""
    if not current_user.has_platform_bypass:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can perform repairs"
        )
    
    update_query = text("""
        UPDATE user_projects up
        SET company_id = s.company_id
        FROM sites s
        WHERE up.site_id = s.id
        AND (up.company_id IS NULL OR up.company_id != s.company_id)
    """)
    result = db_session.execute(update_query)
    db_session.commit()
    
    return RepairResult(
        repair_type="inv1_normalization",
        records_fixed=result.rowcount,
        success=True,
        message=f"Normalized company_id for {result.rowcount} user_projects records"
    )

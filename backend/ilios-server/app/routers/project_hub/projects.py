"""Project Hub project endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_session
from app.models.site import Site, SiteAdditionalFieldList
from app.static.sales import LifecycleState

router = APIRouter()


class ProjectSummary(BaseModel):
    id: int
    name: str
    display_name: str
    constructed_name: Optional[str]
    name_override: Optional[str]
    company_id: int
    company_name: Optional[str]
    lifecycle_state: Optional[str]
    signed_agreement_status: Optional[str]
    system_size_ac: float
    system_size_dc: float
    state: Optional[str]
    city: Optional[str]

    class Config:
        from_attributes = True


class ProjectDetail(ProjectSummary):
    address: Optional[str]
    county: Optional[str]
    zip_code: Optional[str]
    is_agreement_blocking: bool
    has_signed_agreement: bool

    class Config:
        from_attributes = True


class ProjectBlocker(BaseModel):
    type: str
    message: str
    action_url: Optional[str]


class ProjectReadinessResponse(BaseModel):
    project_id: int
    lifecycle_state: Optional[str]
    blockers: List[ProjectBlocker]
    can_advance: bool


@router.get("/projects", response_model=List[ProjectSummary])
def list_projects(
    company_id: Optional[int] = None,
    lifecycle_state: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_session),
):
    """List all projects with optional filters."""
    query = db.query(Site).options(
        joinedload(Site.company),
        joinedload(Site.additional_fields),
    )
    
    if company_id:
        query = query.filter(Site.company_id == company_id)
    
    if lifecycle_state:
        query = query.join(SiteAdditionalFieldList).filter(
            SiteAdditionalFieldList.lifecycle_state == lifecycle_state
        )
    
    sites = query.offset(skip).limit(limit).all()
    
    return [
        ProjectSummary(
            id=site.id,
            name=site.name,
            display_name=site.display_name,
            constructed_name=site.constructed_name,
            name_override=site.name_override,
            company_id=site.company_id,
            company_name=site.company.name if site.company else None,
            lifecycle_state=site.additional_fields.lifecycle_state if site.additional_fields else None,
            signed_agreement_status=site.signed_agreement_status,
            system_size_ac=site.system_size_ac,
            system_size_dc=site.system_size_dc,
            state=site.state.value if site.state else None,
            city=site.city,
        )
        for site in sites
    ]


@router.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(
    project_id: int,
    db: Session = Depends(get_session),
):
    """Get project details."""
    site = db.query(Site).options(
        joinedload(Site.company),
        joinedload(Site.additional_fields),
    ).filter(Site.id == project_id).first()
    
    if not site:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectDetail(
        id=site.id,
        name=site.name,
        display_name=site.display_name,
        constructed_name=site.constructed_name,
        name_override=site.name_override,
        company_id=site.company_id,
        company_name=site.company.name if site.company else None,
        lifecycle_state=site.additional_fields.lifecycle_state if site.additional_fields else None,
        signed_agreement_status=site.signed_agreement_status,
        system_size_ac=site.system_size_ac,
        system_size_dc=site.system_size_dc,
        state=site.state.value if site.state else None,
        city=site.city,
        address=site.address,
        county=site.county,
        zip_code=site.zip_code,
        is_agreement_blocking=site.is_agreement_blocking,
        has_signed_agreement=site.has_signed_agreement,
    )


@router.get("/projects/{project_id}/readiness", response_model=ProjectReadinessResponse)
def get_project_readiness(
    project_id: int,
    db: Session = Depends(get_session),
):
    """Get project readiness status and blockers."""
    site = db.query(Site).options(
        joinedload(Site.additional_fields),
    ).filter(Site.id == project_id).first()
    
    if not site:
        raise HTTPException(status_code=404, detail="Project not found")
    
    blockers = []
    
    if site.signed_agreement_status == "missing":
        blockers.append(ProjectBlocker(
            type="signed_agreement",
            message="Signed agreement (MIPA/Term Sheet) is required",
            action_url=f"/project-hub/{project_id}/data-room"
        ))
    
    lifecycle_state = None
    if site.additional_fields:
        lifecycle_state = site.additional_fields.lifecycle_state
    
    can_advance = len(blockers) == 0
    
    return ProjectReadinessResponse(
        project_id=project_id,
        lifecycle_state=lifecycle_state,
        blockers=blockers,
        can_advance=can_advance,
    )

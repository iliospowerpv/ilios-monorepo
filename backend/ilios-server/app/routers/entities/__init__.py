"""Entity Directory API routes."""

from fastapi import APIRouter

from app.routers.entities.entities import router as entities_router
from app.routers.entities.project_entity_relationships import router as project_relationships_router
from app.routers.entities.deal_entity_assignments import router as deal_assignments_router

router = APIRouter(prefix="/api", tags=["entities"])

router.include_router(entities_router)
router.include_router(project_relationships_router)
router.include_router(deal_assignments_router)

"""Sales module API routes."""

from fastapi import APIRouter

from app.routers.sales.pipeline import router as pipeline_router
from app.routers.sales.projects import router as projects_router

router = APIRouter(prefix="/api/sales", tags=["sales"])

router.include_router(pipeline_router)
router.include_router(projects_router)

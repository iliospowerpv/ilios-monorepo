"""Sales module API routes."""

from fastapi import APIRouter

from app.routers.sales.deals import router as deals_router
from app.routers.sales.projects import router as projects_router

router = APIRouter(prefix="/api/sales", tags=["sales"])

router.include_router(deals_router)
router.include_router(projects_router)

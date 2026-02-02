"""Project Hub router module."""

from fastapi import APIRouter

from .lifecycle import router as lifecycle_router
from .projects import router as projects_router

router = APIRouter(prefix="/project-hub", tags=["Project Hub"])

router.include_router(lifecycle_router)
router.include_router(projects_router)

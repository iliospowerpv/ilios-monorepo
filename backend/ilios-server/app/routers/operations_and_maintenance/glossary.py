"""Glossary endpoint for the V2 "expected production" vocabulary.

Serves the static, tenant-agnostic definitions in
``app.helpers.telemetry.expected_glossary`` so the frontend can render
consistent info tooltips for the expected / actual / status terminology. The
data is read-only reference content (no DB, no provider call); the endpoint only
requires an authenticated user.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.helpers.authentication import get_current_user
from app.helpers.telemetry.expected_glossary import EXPECTED_GLOSSARY
from app.schema.glossary import GlossarySchema

om_glossary_router = APIRouter()


@om_glossary_router.get(
    "",
    response_model=GlossarySchema,
    description="Static glossary of the expected-production terms used across O&M and investor views.",
    dependencies=[Depends(get_current_user)],
)
async def get_expected_glossary():
    return {"terms": EXPECTED_GLOSSARY}

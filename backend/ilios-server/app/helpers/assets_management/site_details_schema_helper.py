from fastapi import HTTPException, Request

from app.static.sites import SITE_AM_SECTIONS_MAPPING


def get_section_schema(request: Request):
    """Retrieve corresponding schema based on the query param"""
    section_name = request.query_params.get("section_name")
    schema = SITE_AM_SECTIONS_MAPPING.get(section_name)
    if not schema:
        expected_sections = ", ".join(SITE_AM_SECTIONS_MAPPING.keys())
        raise HTTPException(status_code=400, detail=f"Invalid <section_name> value, must be one of: {expected_sections}")
    return schema

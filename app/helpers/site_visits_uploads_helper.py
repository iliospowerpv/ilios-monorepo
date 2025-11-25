from fastapi import Request

from app.static.site_visits import SiteVisitsUploads


def get_sv_upload_section(request: Request):
    """Based on the URL path, define is it field discovery or site conditions site visit upload"""
    for upload_type in SiteVisitsUploads:
        if upload_type.value in request.url.path:
            return upload_type

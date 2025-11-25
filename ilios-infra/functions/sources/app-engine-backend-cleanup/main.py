# -*- coding: utf-8 -*-

"""
Cloud Function for App Engine service versions cleanup
"""

import os
import functions_framework
from google.cloud import appengine_admin_v1


@functions_framework.http
def handler(request):
    """Cloud Function entrypoint

    Args:
        request (flask.Request): Trigger event payload.

    Returns:
        Function execution result.

    """
    with appengine_admin_v1.VersionsClient() as client:
        service = f"apps/{os.environ['PROJECT_ID']}/services/backend"

        response = client.list_versions(
            appengine_admin_v1.ListVersionsRequest({
                "parent": service
            })
        )

        for version in response:
            if version.serving_status == appengine_admin_v1.types.ServingStatus.STOPPED:
                client.delete_version(
                    appengine_admin_v1.DeleteVersionRequest({
                        "name": f"{service}/versions/{version.id}"
                    })
                )
                print(f"App version {version.id} deleted.")

    return "OK"

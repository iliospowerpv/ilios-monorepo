import logging
from datetime import datetime, timezone

import requests
from fastapi import HTTPException, status

from app.settings import settings

logger = logging.getLogger(__name__)


class RombusClient:

    def __init__(self):
        """
        Client to cooperate with Rombus API.

        Additional info can be found by following links:
        Rombus DOCS: https://apidocs.rhombussystems.com/docs/introduction
        Rombus APIs: https://apidocs.rhombussystems.com/reference
        """

        self.cameras_list_url = "https://api2.rhombussystems.com/api/camera/getMinimalCameraStateList"
        self.locations_url = "https://api2.rhombussystems.com/api/location/getLocations"
        self.create_shared_livestream_url = "https://api2.rhombussystems.com/api/camera/createSharedLiveVideoStream"
        self.get_shared_livestream_url = "https://api2.rhombussystems.com/api/camera/findSharedLiveVideoStreams"
        self.get_policy_alerts_url = "https://api2.rhombussystems.com/api/event/getPolicyAlerts"
        self.create_shared_clip_group = "https://api2.rhombussystems.com/api/event/createSharedClipGroupV3"
        self.get_shared_clip_groups = "https://api2.rhombussystems.com/api/event/getSharedClipGroupsV2"

        self.ilios_stream_name = "Ilios Stream"

        self.headers = {
            "accept": "application/json",
            "x-auth-scheme": "api-token",
            "content-type": "application/json",
            "x-auth-apikey": settings.rombus_api_key,
        }

    @staticmethod
    def handle_response_error(response):
        if response.status_code != 200:
            status_code = response.json().get("status")
            message = response.json().get("msg")
            logger.warning(f"Rombus call failed with code: {status_code}, message: {message}")
            if status_code and message:
                raise HTTPException(status_code, message)
            else:
                raise HTTPException(
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    "We are currently experiencing an issue with our Security provider. Please try again later.",
                )

    def get_cameras_list(self):
        response = requests.post(self.cameras_list_url, headers=self.headers)
        self.handle_response_error(response)
        return response.json()["cameraStates"]

    def get_locations(self):
        payload = {"subLocationsIncluded": True}
        response = requests.post(self.locations_url, headers=self.headers, json=payload)
        self.handle_response_error(response)
        return response.json()["locations"]

    def create_camera_shared_livestream(self, camera_uuid: str):
        payload = {
            "name": self.ilios_stream_name,
            "includeAudio": True,
            "ssoProtected": False,
            "streamType": "USER",
            "vodEnabled": True,
            "cameraUuid": camera_uuid,
        }
        response = requests.post(self.create_shared_livestream_url, json=payload, headers=self.headers)
        self.handle_response_error(response)
        return response.json()

    def get_or_create_shared_livestream(self, camera_uuid: str):
        """
        Get camera livestream, filter by stream name for ilisos 'Ilios Stream'. If such stream does not exist,
        create one.
        """
        payload = {"cameraUuid": camera_uuid}
        response = requests.post(self.get_shared_livestream_url, json=payload, headers=self.headers)
        self.handle_response_error(response)
        ilios_live_streams = (
            [
                stream
                for stream in response.json()["sharedLiveVideoStreams"]
                if stream.get("name") == self.ilios_stream_name
            ]
            if response.json()["sharedLiveVideoStreams"]
            else None
        )
        # Create live video stream if not exists
        if not ilios_live_streams:
            return self.create_camera_shared_livestream(camera_uuid)
        return ilios_live_streams[0]

    def get_policy_alerts(self, cameras_uuids: list):
        """Get all policy alerts. Each alert includes device id and can be filtered by camera UUID."""
        payload = {"deviceFilter": cameras_uuids}
        response = requests.post(self.get_policy_alerts_url, headers=self.headers, json=payload)
        self.handle_response_error(response)
        return response.json()["policyAlerts"]

    def create_shared_alert_clip_url(self, alert_uuid: str):
        # Send empty 'tite' and 'description' - without those fields url is created but clip is not working
        payload = {"title": "", "description": "", "uuids": [{"alertUuid": alert_uuid}]}
        response = requests.post(self.create_shared_clip_group, json=payload, headers=self.headers)
        self.handle_response_error(response)
        return response.json()["shareUrl"]

    def get_or_create_shared_alert_clip_url(self, alert_uuid: str):
        """
        Get alert video url if exists, otherwise create new shared video clip url.
        Rombus does not store alerts shared clips url, but it stores shared groups which uuid is also video clip uuid.
        Alert shared clip url is: 'https://console.rhombussystems.com/share/clips/' + shared clip group uuid.
        Filtering for shared groups is done by time in milliseconds.
        """
        try:
            # Search for existing alert shared clips urls created before current time
            time_in_milliseconds = int(datetime.now(timezone.utc).timestamp() * 1000)
            payload = {"createdBeforeMs": time_in_milliseconds}
            response = requests.post(self.get_shared_clip_groups, json=payload, headers=self.headers)
            self.handle_response_error(response)
            for shared_clip_group in response.json().get("sharedClipGroups", []):
                shared_clips_uuids = [clip.get("uuid") for clip in shared_clip_group.get("sharedClips", [])]
                if alert_uuid in shared_clips_uuids:
                    # Shared clip group uuid is an uuid of alert shared video clip
                    return "https://console.rhombussystems.com/share/clips/" + shared_clip_group["uuid"]
            return self.create_shared_alert_clip_url(alert_uuid)
        except Exception as exc:
            logger.warning(f"An error occurred during shared clip retrieval for alert <{alert_uuid}>: {str(exc)}")
            raise HTTPException(status_code=400, detail=f"Rombus call failed with an error: {str(exc)}")

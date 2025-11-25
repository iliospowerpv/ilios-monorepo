TEST_CAMERA_UUID = "123AAsfa-mo"
TEST_CAMERA_NAME = "ROMBUS CAMERA"
TEST_CAMERA_LIVESTREAM_URL = "https://rombus/camera/stream"
TEST_ALERT_UUID = "123AAsfacsacf"
TEST_LOCATION_UUID = "asdsd32fdsf"
TEST_SHARED_CLIP_UUID = "ghjsfas1231"

TEST_ROMBUS_CAMERAS_RESPONSE = {
    "cameraStates": [
        {
            "name": TEST_CAMERA_NAME,
            "uuid": TEST_CAMERA_UUID,
            "connectionStatus": "GREEN",
            "locationUuid": TEST_LOCATION_UUID,
        }
    ]
}

TEST_ROMBUS_ALERTS_RESPONSE = {
    "policyAlerts": [
        {
            "uuid": TEST_ALERT_UUID,
            "deviceUuid": TEST_CAMERA_UUID,
            "name": "Ilios Stream",
            "policyAlertTriggers": ["MOTION_HUMAN"],
            "timestampMs": 1723800933073,
        }
    ]
}


TEST_ROMBUS_LIVESTREAM_RESPONSE = {
    "sharedLiveVideoStreams": [
        {
            "uuid": "stream uuid",
            "name": "Ilios Stream",
            "sharedLiveVideoStreamUrl": TEST_CAMERA_LIVESTREAM_URL,
        }
    ]
}

TEST_ALERT_SHARED_CLIPS_RESPONSE = {
    "sharedClipGroups": [{"sharedClips": [{"uuid": TEST_ALERT_UUID}], "uuid": TEST_SHARED_CLIP_UUID}]
}

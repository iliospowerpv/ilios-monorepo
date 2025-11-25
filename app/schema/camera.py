from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BaseCameraSchema(BaseModel):
    name: str = Field(examples=["DATA CENTER"])
    uuid: str = Field(examples=["LmHs3wpJRAqG05r_CKTjOA"])


class PotentialCamerasList(BaseModel):
    items: Optional[list[BaseCameraSchema]]


class SiteCameraSchema(BaseCameraSchema):
    location: str = Field(examples=["ARCADIA, NY - BULLROCK"])
    status: str = Field(examples=["GREEN"])


class SiteCamerasList(BaseModel):
    items: Optional[list[SiteCameraSchema]]


class CameraLiveStreamURL(BaseModel):
    live_stream_url: str = Field(examples=["https://rombus/camera/stream"])


class CameraAlertSchema(BaseModel):
    alert_uuid: str = Field("5re3xQmjToiaIWZpnjjhPg")
    alert_type: str = Field(examples=["Human Movement"])
    camera_name: str = Field(examples=["ROMBUS CAMERA"])
    timestamp: datetime = Field(examples=["2021-08-01T00:00:00"])


class CamerasAlertsList(BaseModel):
    items: Optional[list[CameraAlertSchema]]


class AlertSharedClipURL(BaseModel):
    shared_clip_url: str = Field(examples=["https://rombus/alerts/s12sd"])

import enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from pydantic.networks import IPvAnyAddress


class YesNoDropdown(enum.Enum):
    yes = "Yes"
    no = "No"  # noqa: VNE002


class IPAddressSchema(BaseModel):
    ip_address: Optional[IPvAnyAddress] = Field(None, examples=["192.168.0.1"], title="IP Address")

    @field_validator("ip_address")
    @classmethod
    def transform_ip_to_string(cls, ip_address_value):
        """Serialize to the string to handle error:
        <sqlalchemy.exc.StatementError: (builtins.TypeError) Object of type IPv4Address is not JSON serializable>"""
        # return if no IP Address is set, to avoid having: str(None) -> "None"
        if not ip_address_value:
            return

        return str(ip_address_value)


class CommunicationSectionSchema(IPAddressSchema):
    port: Optional[int] = Field(None, examples=[80], title="Port")
    serial_mode: Optional[str] = Field(None, examples=["RS-485, 2 wire"], title="Serial Mode", max_length=100)
    baud: Optional[float] = Field(None, examples=[2.12], title="Baud")

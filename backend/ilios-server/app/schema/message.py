"""API Schema for messages-related Endpoints"""

from pydantic import BaseModel, Field


class Error(BaseModel):
    message: str = Field(
        description="Error description",
        examples=[
            "Not found",
            "Validation error description",
            "Internal server error description",
        ],
    )
    code: int = Field(
        description="Error status code",
        examples=[400, 400, 500],
    )


class Success(BaseModel):
    message: str = Field(description="Success message", examples=["OK", "Created", "Accepted", "No Content"])
    code: int = Field(description="Success status code", examples=[200, 201, 202, 204])


class BadRequestError(Error):
    code: int = 400

from pydantic import BaseModel, Field

from app.schema.user import UserEmailSchema


class Token(BaseModel):
    access_token: str = Field(examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzeXN0ZW1AdXN.AzvGQHkqpYL7Tb"])
    token_type: str = Field(examples=["bearer"])


class UserLoginSchema(UserEmailSchema):

    password: str = Field(examples=["789"])


class ResetPasswordSchema(UserEmailSchema):
    pass

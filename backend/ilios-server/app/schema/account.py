"""Place for account endpoints schemas."""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class PasswordSetupPayload(BaseModel):
    password: str
    email: EmailStr
    token: str

    @field_validator("password")
    @classmethod
    def verify_password(cls, password: str) -> str:
        """Verify password using Python regex.

        By default, Pydantic uses Rust for regexes handling, and it doesn't support look-around syntax (like (?=)
        groups).
        """
        # no white-space; length of min 8 and max 255 symbols; at least 1 digit, 1 lower-case char, 1 upper-case;
        # at least one special symbol from the list: ~`!@#$%^&*()-_+={}[]|\;:"<>,./?
        pattern = re.compile(
            r"^(?=.*[0-9])(?=.*[a-z])(?=.*[A-Z])"
            r'(?=.*[~`!@#$%^&*()_+={}[\]\|\\;:"<>,.\/\?\-])'
            r'[a-zA-Z0-9~`!@#$%^&*()_+={}[\]\|\\;:"<>,.\/\?\-]{8,255}$'
        )

        if not pattern.match(password):
            raise ValueError("Password doesn't match required criteria")
        return password


class PasswordCreationSuccess(BaseModel):
    message: str = Field(description="Success message", examples=["Password has been set successfully"])
    code: int = Field(description="Success status code", examples=[200])

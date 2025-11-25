from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class AuthRequest(BaseModel):
    user_id: int
    company_id: int
    site_id: int


class AuthResponse(BaseModel):
    token: Token
    session_id: str

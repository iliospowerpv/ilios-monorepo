from pydantic import BaseModel, Field

from app.schema import Token


class ChatbotSessionTokenSchema(BaseModel):
    token: Token
    session_id: str = Field(examples=["c3c48937-8c52-ff06e7bfb8bc-5f88-96a2"])

"""AI Assistant API schemas (Slice 1 — read-only chat).

The native AI Assistant is a READ-ONLY orchestration advisor. It can explain workflows,
recommend next actions, and answer help/FAQ/product questions by calling the SAME authorized
read-only services the Workflow Dashboard uses. It never starts, previews, executes, or mutates
anything — every workflow launch remains a human action through the existing engine handshake.

Slice 1 is STATELESS: the client may send prior turns in ``history`` (conversation persistence is
a later slice). ``context`` carries optional, advisory route/entity hints from the FE so replies can
be page-aware; the assistant still resolves all data through authz-scoped tools, never from hints.
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "assistant_chat.v1"


class AssistantContextHints(BaseModel):
    """Optional, advisory UI context. NEVER used to widen authorization or to fabricate data —
    only to help the assistant phrase page-relevant guidance. All data is still fetched via the
    authz-scoped read-only tools."""

    route: Optional[str] = Field(default=None, examples=["/project-hub/companies/3"])
    company_id: Optional[int] = Field(default=None, examples=[3])
    site_id: Optional[int] = Field(default=None, examples=[1])
    project_id: Optional[int] = Field(
        default=None,
        description="Alias of site_id in UI terminology (Project == Site).",
        examples=[1],
    )


class AssistantMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    # Prior turns supplied by the client (stateless MVP). Bounded to keep prompts sane.
    history: list[AssistantMessage] = Field(default_factory=list, max_length=20)
    context: Optional[AssistantContextHints] = None
    # Echoed back; persistence is a later slice, so this is not yet authoritative.
    conversation_id: Optional[str] = None


class AssistantToolInvocation(BaseModel):
    """Transparency record of a single read-only tool the assistant invoked this turn."""

    name: str
    ok: bool
    error: Optional[str] = None


class AssistantChatResponse(BaseModel):
    schema_version: str = SCHEMA_VERSION
    # Always "read_only_advice" — mirrors the orchestration-context contract.
    mode: Literal["read_only_advice"] = "read_only_advice"
    generated_at: datetime
    conversation_id: Optional[str] = None
    model: str
    reply: str
    # Which read-only tools were used (for transparency / FE "sources" disclosure / audit).
    used_tools: list[AssistantToolInvocation] = Field(default_factory=list)

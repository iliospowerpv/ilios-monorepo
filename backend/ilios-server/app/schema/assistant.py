"""AI Assistant API schemas.

The native AI Assistant is a READ-ONLY orchestration advisor. It can explain workflows,
recommend next actions, and answer help/FAQ/product questions by calling the SAME authorized
read-only services the Workflow Dashboard uses. It never starts, previews, executes, or mutates
anything — every workflow launch remains a human action through the existing engine handshake.

Slice 2 additions (all ADDITIVE, backward compatible with Slice 1):
- ``context`` still carries optional, advisory route/entity hints from the FE so replies can be
  page-aware; the assistant still resolves all data through authz-scoped tools, never from hints.
- ``AssistantActionCard`` + ``action_cards`` on the response: PROPOSE-ONLY deep links. A card is a
  validated, read-only suggestion the USER clicks to open the relevant wizard/run in the existing
  workflow UI. The assistant never starts/executes it — the card carries ``requires_user_action``.
- Conversation persistence: ``persist`` on the request + conversation list/detail schemas. Stored
  ONLY in the isolated ``assistant_conversations`` tables (nothing shared with the legacy chatbot).
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "assistant_chat.v2"


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
    # Prior turns supplied by the client (stateless reasoning path). Bounded to keep prompts sane.
    history: list[AssistantMessage] = Field(default_factory=list, max_length=20)
    context: Optional[AssistantContextHints] = None
    # When set (or when ``persist`` is true), the turn is recorded in the isolated assistant
    # conversation store and the resolved conversation id is echoed on the response.
    conversation_id: Optional[str] = None
    persist: bool = False


class AssistantToolInvocation(BaseModel):
    """Transparency record of a single read-only tool the assistant invoked this turn."""

    name: str
    ok: bool
    error: Optional[str] = None


class AssistantSource(BaseModel):
    """A LABELS-ONLY disclosure of a knowledge source that backed an assistant turn (Slice 3).

    Never carries raw tool payloads — only a stable identifier/label so the UI can transparently
    show what the answer was grounded on. ``kind='faq'`` carries the curated entry id + question +
    category; ``kind='tool'`` carries the read-only tool name + a friendly label.
    """

    kind: Literal["faq", "tool"]
    label: str
    ref: Optional[str] = Field(default=None, description="Stable id (faq entry id / tool name).")
    detail: Optional[str] = Field(default=None, description="Extra context (faq question/category).")


class AssistantActionCard(BaseModel):
    """A PROPOSE-ONLY next-step the user can take. It is a validated deep link into the EXISTING
    workflow UI — never an execution. The assistant produced it after a read-only permission check
    (the user can start/resume the target); clicking it navigates the user's browser to the wizard
    where THEY perform the governed handshake. ``requires_user_action`` is always true."""

    kind: Literal["workflow", "sequence", "resume"]
    title: str
    reason: str
    route: str
    workflow_id: Optional[str] = None
    sequence_id: Optional[str] = None
    run_id: Optional[int] = None
    target_site_id: Optional[int] = None
    target_company_id: Optional[int] = None
    requires_user_action: bool = True


class AssistantChatResponse(BaseModel):
    schema_version: str = SCHEMA_VERSION
    # Always "read_only_advice" — mirrors the orchestration-context contract.
    mode: Literal["read_only_advice"] = "read_only_advice"
    generated_at: datetime
    conversation_id: Optional[str] = None
    model: str
    reply: str
    # Which read-only tools were used (for transparency / audit).
    used_tools: list[AssistantToolInvocation] = Field(default_factory=list)
    # Labels-only disclosure of the knowledge sources (FAQ entries / data tools) backing the reply.
    sources: list[AssistantSource] = Field(default_factory=list)
    # Propose-only deep-link cards the user may click. Never auto-executed.
    action_cards: list[AssistantActionCard] = Field(default_factory=list)
    # Persisted assistant-turn id (only when the turn was stored), so the FE can attach feedback to
    # the just-sent reply. Null for non-persisted chats.
    message_id: Optional[int] = None


# --- Conversation persistence (isolated assistant store) ----------------------------------------


class AssistantPersistedMessage(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    used_tools: list[AssistantToolInvocation] = Field(default_factory=list)
    sources: list[AssistantSource] = Field(default_factory=list)
    action_cards: list[AssistantActionCard] = Field(default_factory=list)
    model: Optional[str] = None
    feedback: Optional[Literal["up", "down"]] = None
    feedback_note: Optional[str] = None
    created_at: datetime


class AssistantConversationSummary(BaseModel):
    id: int
    title: Optional[str] = None
    company_id: Optional[int] = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class AssistantConversationListResponse(BaseModel):
    items: list[AssistantConversationSummary] = Field(default_factory=list)


class AssistantConversationDetailResponse(BaseModel):
    id: int
    title: Optional[str] = None
    company_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    messages: list[AssistantPersistedMessage] = Field(default_factory=list)


class AssistantConfigResponse(BaseModel):
    """Lightweight capability/probe payload. Reachable ONLY when the feature flag is on (the router
    404s otherwise), so the FE treats a successful fetch as 'assistant available'."""

    enabled: bool = True
    model: str
    mode: Literal["read_only_advice"] = "read_only_advice"
    available_tools: list[str] = Field(default_factory=list)
    prohibited_actions: list[str] = Field(default_factory=list)


# --- Feedback (Slice 3) -------------------------------------------------------------------------


class AssistantFeedbackRequest(BaseModel):
    """Owner-supplied thumbs rating on a persisted assistant turn. Writes ONLY to the isolated
    assistant message row (never a governed/business action). ``rating=None`` clears the rating."""

    rating: Optional[Literal["up", "down"]] = None
    note: Optional[str] = Field(default=None, max_length=2000)


class AssistantFeedbackResponse(BaseModel):
    message_id: int
    feedback: Optional[Literal["up", "down"]] = None
    feedback_note: Optional[str] = None


# --- Suggested prompts (Slice 3) ----------------------------------------------------------------


class AssistantSuggestedPrompt(BaseModel):
    """A static, page-aware example question. Pure UI affordance — carries no live/business state."""

    label: str
    prompt: str


class AssistantSuggestedPromptsResponse(BaseModel):
    # Echoes the resolved route bucket used to pick prompts (advisory/debug only).
    context_label: Optional[str] = None
    prompts: list[AssistantSuggestedPrompt] = Field(default_factory=list)


# --- Admin usage observability (Slice 3) --------------------------------------------------------


class AssistantToolUsageStat(BaseModel):
    name: str
    count: int


class AssistantUsageResponse(BaseModel):
    """Read-only aggregate over ONLY the isolated assistant tables. No business/operational data."""

    conversations_total: int = 0
    conversations_active: int = 0
    conversations_archived: int = 0
    messages_total: int = 0
    user_messages: int = 0
    assistant_messages: int = 0
    distinct_users: int = 0
    feedback_up: int = 0
    feedback_down: int = 0
    feedback_none: int = 0
    top_tools: list[AssistantToolUsageStat] = Field(default_factory=list)

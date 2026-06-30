"""Architecture reference API (superuser-only, read-only).

Powers the System Settings -> Architecture tab:

- ``GET /api/settings/architecture/database`` — live ``information_schema``
  introspection of the application (``public``) schema: tables, columns, types.
- ``GET /api/settings/architecture/docs`` — list of curated, allowlisted
  architecture / operational markdown documents that exist on disk.
- ``GET /api/settings/architecture/docs/{doc_key}`` — the raw markdown content of
  one allowlisted document.

Security: documents are served via an explicit ``key -> repo-relative path``
allowlist (no user-supplied path ever reaches the filesystem), and the resolved
path is additionally verified to live under the repo root, so path traversal is
not possible. Database introspection is limited to the ``public`` schema and is
restricted to platform-bypass users.
"""

import logging
from pathlib import Path
from typing import Annotated, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.helpers.authorization.module_based.base import get_current_admin_user
from app.schema.user import CurrentUserSchema

architecture_router = APIRouter()
logger = logging.getLogger(__name__)

# Repo root: .../backend/ilios-server/app/routers/settings/architecture.py
#   parents[0]=settings [1]=routers [2]=app [3]=ilios-server [4]=backend [5]=repo root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_MAX_DOC_BYTES = 500_000

# Curated, explicit allowlist: key -> (title, repo-relative path).
# Only these keys are serveable; nothing user-supplied reaches the filesystem.
_DOC_ALLOWLIST: dict = {
    "project-overview": ("Project Overview & Architecture (replit.md)", "replit.md"),
    "backend-modules": ("Backend Module Reference", "docs/architecture/backend-modules.md"),
    "runbook": ("Operational Runbook", "docs/RUNBOOK.md"),
    "technical-debt": ("Technical Debt Register", "docs/technical_debt_register.md"),
    "ai-development-guardrails": ("AI Development Guardrails", "docs/AI_DEVELOPMENT_GUARDRAILS.md"),
    "documentation-requirements": ("Documentation Requirements", "docs/DOCUMENTATION_REQUIREMENTS.md"),
    "access-model": ("Access Model Audit", "docs/access_model_audit.md"),
    "portfolio-hub-model": ("Portfolio Hub Model", "docs/portfolio_hub_model.md"),
}


class ColumnInfo(BaseModel):
    name: str
    data_type: str
    is_nullable: bool


class TableInfo(BaseModel):
    name: str
    column_count: int
    columns: List[ColumnInfo]


class DatabaseStructureResponse(BaseModel):
    schema_name: str
    table_count: int
    tables: List[TableInfo]


class DocSummary(BaseModel):
    key: str
    title: str
    path: str
    size_bytes: int


class DocListResponse(BaseModel):
    documents: List[DocSummary]


class DocContentResponse(BaseModel):
    key: str
    title: str
    path: str
    content: str
    truncated: bool


def _resolve_doc(doc_key: str) -> Optional[Tuple[str, str, Path]]:
    """Return (title, repo-relative path, absolute Path) for an allowlisted, existing doc."""
    entry = _DOC_ALLOWLIST.get(doc_key)
    if not entry:
        return None
    title, rel_path = entry
    abs_path = (_REPO_ROOT / rel_path).resolve()
    # Defence-in-depth: the resolved path must live under the repo root.
    if _REPO_ROOT != abs_path and _REPO_ROOT not in abs_path.parents:
        logger.warning("Architecture doc %s resolved outside repo root", doc_key)
        return None
    if not abs_path.is_file():
        return None
    return title, rel_path, abs_path


@architecture_router.get(
    "/database",
    response_model=DatabaseStructureResponse,
    summary="Database structure (information_schema)",
    description="Introspect the application (public) schema: tables, columns and types. Superuser-only.",
)
async def get_database_structure(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_admin_user)],
    db_session: Session = Depends(get_session),
) -> DatabaseStructureResponse:
    rows = db_session.execute(
        text(
            """
            SELECT table_name, column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
            """
        )
    ).fetchall()

    tables: List[TableInfo] = []
    current_name: Optional[str] = None
    current_columns: List[ColumnInfo] = []
    for row in rows:
        if row.table_name != current_name:
            if current_name is not None:
                tables.append(
                    TableInfo(name=current_name, column_count=len(current_columns), columns=current_columns)
                )
            current_name = row.table_name
            current_columns = []
        current_columns.append(
            ColumnInfo(
                name=row.column_name,
                data_type=row.data_type,
                is_nullable=(row.is_nullable == "YES"),
            )
        )
    if current_name is not None:
        tables.append(TableInfo(name=current_name, column_count=len(current_columns), columns=current_columns))

    return DatabaseStructureResponse(schema_name="public", table_count=len(tables), tables=tables)


@architecture_router.get(
    "/docs",
    response_model=DocListResponse,
    summary="List architecture / operational documents",
    description="Curated, allowlisted markdown documents that exist on disk. Superuser-only.",
)
async def list_docs(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_admin_user)],
) -> DocListResponse:
    documents: List[DocSummary] = []
    for key in _DOC_ALLOWLIST:
        resolved = _resolve_doc(key)
        if not resolved:
            continue
        title, rel_path, abs_path = resolved
        documents.append(
            DocSummary(key=key, title=title, path=rel_path, size_bytes=abs_path.stat().st_size)
        )
    return DocListResponse(documents=documents)


@architecture_router.get(
    "/docs/{doc_key}",
    response_model=DocContentResponse,
    summary="Read one architecture / operational document",
    description="Return the raw markdown for an allowlisted document. Superuser-only.",
)
async def get_doc(
    doc_key: str,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_admin_user)],
) -> DocContentResponse:
    resolved = _resolve_doc(doc_key)
    if not resolved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    title, rel_path, abs_path = resolved

    raw = abs_path.read_bytes()
    truncated = len(raw) > _MAX_DOC_BYTES
    content = raw[:_MAX_DOC_BYTES].decode("utf-8", errors="replace")

    return DocContentResponse(
        key=doc_key, title=title, path=rel_path, content=content, truncated=truncated
    )

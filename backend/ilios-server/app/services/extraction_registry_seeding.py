"""DD V2 Phase 1B — generic extraction-coverage seeding.

This module makes *every* ``SiteDocumentsEnum`` document type eligible for in-app
AI parsing by ensuring it has, in the Extraction Registry:

1. an :class:`ExtractionDocumentType` row (``is_parsable=True``),
2. an **active** schema version wired to a small set of generic canonical fields,
3. an **active** prompt template (the registry default templates).

Design constraints (DD V2 Phase 1, additive-only):

* It NEVER mutates or deactivates an existing active schema/prompt. The ~17
  specialized document types seeded from ``ai_parsing_config.json`` already have an
  active schema + prompt, so they are skipped untouched — their specialized fields
  always win.
* It is fully idempotent / re-runnable: a generic schema/prompt is only added when
  the document type has *no active one*, and a document type / canonical field is
  matched by its normalized ``name`` before being created. Running it twice is a
  no-op.
* It is written with SQLAlchemy Core (``connection.execute(text(...))``) so it can
  be driven from an Alembic migration's bind without depending on ORM session
  ordering, and re-run standalone via :func:`run`.

The matching/normalization rules mirror ``dev_scripts/seed_extraction_registry.py``
so the normalized names line up exactly with the existing specialized rows (which is
what lets us skip them by name).
"""

from __future__ import annotations

import re
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from app.models.extraction_registry import (
    DEFAULT_EXTRACTION_PROMPT,
    DEFAULT_SYSTEM_PROMPT,
)
from app.static.default_site_documents_enum import SiteDocumentsEnum
from app.static.due_diligence_bq_keys import DueDiligenceBQKeys

# Marker stored on rows this seeder creates, so a downgrade can find and remove
# exactly the generic rows without touching specialized (config-seeded) ones.
GENERIC_SCHEMA_NOTES = "DD V2 Phase 1B generic extraction coverage (auto-seeded)"
GENERIC_PROMPT_NOTES = "DD V2 Phase 1B generic extraction coverage (auto-seeded)"

GENERIC_MODEL_NAME = "claude-sonnet-4-5"
GENERIC_TEMPERATURE = 0.0
GENERIC_MAX_TOKENS = 8000

# Display names that are not real, parsable document types.
EXCLUDED_DISPLAY_NAMES = {"Custom"}

# Generic, document-agnostic fields. (display_name, field_type)
GENERIC_FIELDS: list[tuple[str, str]] = [
    ("Document Title", "text"),
    ("Document Date", "date"),
    ("Counterparties", "text"),
    ("Effective Date", "date"),
    ("Expiration or Termination Date", "date"),
    ("Term or Duration", "text"),
    ("Key Obligations", "text"),
    ("Key Amounts or Fees", "currency"),
    ("Governing Law or Jurisdiction", "text"),
    ("Summary", "text"),
]

# --- DD V2 Phase 1C: PVsyst (As-Built, Second Buyer) specialized schema v2 ---
# Normalized name of the existing specialized PVsyst doc type (seeded from config).
PVSYST_DOC_TYPE_NAME = "pv_syst_as_built_second_buyer_report"
PVSYST_SCHEMA_NOTES = "DD V2 Phase 1C PVsyst specialized schema v2 (baseline-aware, auto-seeded)"
PVSYST_PROMPT_NOTES = "DD V2 Phase 1C PVsyst specialized prompt v2 (baseline-aware, auto-seeded)"

PVSYST_SYSTEM_PROMPT = """You are a solar PVsyst report extraction specialist. Extract the requested fields from an As-Built PVsyst production report. Follow these rules strictly:

1. Extract ONLY the fields listed in the extraction request.
2. Return valid JSON matching the exact schema provided.
3. For each field, include evidence: page number, relevant text snippet, and anchor text.
4. Be especially precise with the equipment and monthly production figures that drive the energy-production baseline — module wattage/quantity, inverter wattage/quantity, and each month's Year-1 estimated production. Preserve the document's numeric values and units exactly; never round, infer, or fabricate them.
5. If a field value cannot be found, set value to null but still provide your best guess at where it might appear.
6. Preserve exact wording for text fields when quoting from the document."""


def _normalize(value: str) -> str:
    """Normalize a display name to a stable snake_case key.

    Mirrors ``dev_scripts/seed_extraction_registry.py`` so normalized names match
    the existing specialized rows exactly.
    """
    normalized = value.lower()
    normalized = re.sub(r"[^a-z0-9\s]", "", normalized)
    normalized = re.sub(r"\s+", "_", normalized.strip())
    return normalized


def _categorize(display_name: str) -> str:
    name_lower = display_name.lower()
    if any(x in name_lower for x in ["agreement", "contract", "lease", "ppa", "o&m"]):
        return "legal"
    if any(x in name_lower for x in ["pv syst", "pvsyst", "technical", "interconnection", "appraisal"]):
        return "technical"
    if any(x in name_lower for x in ["tax", "loan", "title", "insurance", "finance", "funding"]):
        return "financial"
    return "other"


def _get_or_create_canonical_field(connection: Connection, display_name: str, field_type: str) -> int:
    name = _normalize(display_name)
    row = connection.execute(
        sa.text("SELECT id FROM canonical_fields WHERE name = :name"),
        {"name": name},
    ).first()
    if row:
        return row[0]
    return connection.execute(
        sa.text(
            "INSERT INTO canonical_fields (name, display_name, field_type, is_active) "
            "VALUES (:name, :display_name, :field_type, true) RETURNING id"
        ),
        {"name": name, "display_name": display_name, "field_type": field_type},
    ).scalar_one()


def _get_or_create_doc_type(connection: Connection, display_name: str, stats: dict) -> int:
    name = _normalize(display_name)
    row = connection.execute(
        sa.text("SELECT id FROM extraction_document_types WHERE name = :name"),
        {"name": name},
    ).first()
    if row:
        return row[0]
    doc_type_id = connection.execute(
        sa.text(
            "INSERT INTO extraction_document_types (name, display_name, category, is_parsable, is_active) "
            "VALUES (:name, :display_name, :category, true, true) RETURNING id"
        ),
        {"name": name, "display_name": display_name, "category": _categorize(display_name)},
    ).scalar_one()
    stats["doc_types_created"] += 1
    return doc_type_id


def _has_active(connection: Connection, table: str, doc_type_id: int) -> bool:
    return (
        connection.execute(
            sa.text(
                f"SELECT 1 FROM {table} WHERE document_type_id = :id AND is_active = true LIMIT 1"
            ),
            {"id": doc_type_id},
        ).first()
        is not None
    )


def _next_version(connection: Connection, table: str, doc_type_id: int) -> int:
    return connection.execute(
        sa.text(f"SELECT COALESCE(MAX(version), 0) + 1 FROM {table} WHERE document_type_id = :id"),
        {"id": doc_type_id},
    ).scalar_one()


def _ensure_generic_schema(connection: Connection, doc_type_id: int, stats: dict) -> None:
    if _has_active(connection, "extraction_schema_versions", doc_type_id):
        return

    version = _next_version(connection, "extraction_schema_versions", doc_type_id)
    schema_id = connection.execute(
        sa.text(
            "INSERT INTO extraction_schema_versions (document_type_id, version, is_active, notes) "
            "VALUES (:id, :version, true, :notes) RETURNING id"
        ),
        {"id": doc_type_id, "version": version, "notes": GENERIC_SCHEMA_NOTES},
    ).scalar_one()
    stats["schema_versions_created"] += 1

    for priority, (display_name, field_type) in enumerate(GENERIC_FIELDS, start=1):
        canonical_field_id = _get_or_create_canonical_field(connection, display_name, field_type)
        already_linked = connection.execute(
            sa.text(
                "SELECT 1 FROM extraction_schema_version_fields "
                "WHERE schema_version_id = :s AND canonical_field_id = :c LIMIT 1"
            ),
            {"s": schema_id, "c": canonical_field_id},
        ).first()
        if already_linked:
            continue
        connection.execute(
            sa.text(
                "INSERT INTO extraction_schema_version_fields "
                "(schema_version_id, canonical_field_id, is_required, extraction_priority) "
                "VALUES (:s, :c, false, :p)"
            ),
            {"s": schema_id, "c": canonical_field_id, "p": priority * 10},
        )
        stats["fields_linked"] += 1


def _ensure_generic_prompt(connection: Connection, doc_type_id: int, stats: dict) -> None:
    if _has_active(connection, "extraction_prompt_templates", doc_type_id):
        return

    version = _next_version(connection, "extraction_prompt_templates", doc_type_id)
    connection.execute(
        sa.text(
            "INSERT INTO extraction_prompt_templates "
            "(document_type_id, version, is_active, system_prompt, extraction_prompt, "
            " model_name, temperature, max_tokens, notes) "
            "VALUES (:id, :version, true, :system_prompt, :extraction_prompt, "
            " :model_name, :temperature, :max_tokens, :notes)"
        ),
        {
            "id": doc_type_id,
            "version": version,
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
            "extraction_prompt": DEFAULT_EXTRACTION_PROMPT,
            "model_name": GENERIC_MODEL_NAME,
            "temperature": GENERIC_TEMPERATURE,
            "max_tokens": GENERIC_MAX_TOKENS,
            "notes": GENERIC_PROMPT_NOTES,
        },
    )
    stats["prompt_templates_created"] += 1


def seed_generic_extraction_coverage(connection: Connection) -> dict:
    """Ensure every SiteDocumentsEnum document type is parse-eligible.

    Idempotent and additive: existing active schemas/prompts are never modified.
    Returns a stats dict describing what was created.
    """
    stats = {
        "doc_types_created": 0,
        "schema_versions_created": 0,
        "prompt_templates_created": 0,
        "fields_linked": 0,
    }

    seen: set[str] = set()
    for member in SiteDocumentsEnum:
        display_name = member.value
        if display_name in EXCLUDED_DISPLAY_NAMES:
            continue
        name = _normalize(display_name)
        if not name or name in seen:
            continue
        seen.add(name)

        doc_type_id = _get_or_create_doc_type(connection, display_name, stats)
        _ensure_generic_schema(connection, doc_type_id, stats)
        _ensure_generic_prompt(connection, doc_type_id, stats)

    return stats


def remove_generic_extraction_coverage(connection: Connection) -> dict:
    """Best-effort reversal: remove only the generic (marker-tagged) schemas/prompts.

    Document type and canonical field catalog rows are intentionally left in place
    (they are additive catalog entries referenced by name elsewhere); removing the
    generic active schema/prompt is what actually reverts parse-eligibility.
    """
    stats = {"schema_versions_deleted": 0, "prompt_templates_deleted": 0}

    # Field links cascade-delete with their schema version.
    result = connection.execute(
        sa.text("DELETE FROM extraction_schema_versions WHERE notes = :notes"),
        {"notes": GENERIC_SCHEMA_NOTES},
    )
    stats["schema_versions_deleted"] = result.rowcount or 0

    result = connection.execute(
        sa.text("DELETE FROM extraction_prompt_templates WHERE notes = :notes"),
        {"notes": GENERIC_PROMPT_NOTES},
    )
    stats["prompt_templates_deleted"] = result.rowcount or 0

    return stats


def seed_pvsyst_specialized_schema_v2(connection: Connection) -> dict:
    """DD V2 Phase 1C — add a baseline-aware specialized schema/prompt v2 for the
    As-Built (Second Buyer) PVsyst report.

    Behavior:
      * Clones the current active schema's field set into a new v2 (so every existing
        display-name key is retained — nothing is lost), then guarantees every
        baseline-driving field (``DueDiligenceBQKeys``) is present and marked
        required.
      * Adds a specialized v2 prompt that emphasizes precise extraction of the
        baseline-driving equipment/production figures.
      * Flips ``is_active`` so v2 becomes the active schema/prompt; the prior v1 rows
        are deactivated but NEVER mutated (their fields/content are untouched).

    Idempotent: if a marker-tagged v2 already exists for the doc type, it is a no-op.
    Defensive no-op if the PVsyst doc type does not exist.
    """
    stats = {
        "schema_v2_created": False,
        "prompt_v2_created": False,
        "fields_cloned": 0,
        "baseline_fields_marked_required": 0,
    }

    doc_type_row = connection.execute(
        sa.text("SELECT id FROM extraction_document_types WHERE name = :name"),
        {"name": PVSYST_DOC_TYPE_NAME},
    ).first()
    if not doc_type_row:
        return stats
    doc_type_id = doc_type_row[0]

    baseline_field_ids: set[int] = set()
    for display_name in DueDiligenceBQKeys.list():
        baseline_field_ids.add(_get_or_create_canonical_field(connection, display_name, "text"))

    # --- Schema v2 ---
    already_seeded_schema = connection.execute(
        sa.text(
            "SELECT 1 FROM extraction_schema_versions "
            "WHERE document_type_id = :id AND notes = :notes LIMIT 1"
        ),
        {"id": doc_type_id, "notes": PVSYST_SCHEMA_NOTES},
    ).first()

    if not already_seeded_schema:
        active_schema = connection.execute(
            sa.text(
                "SELECT id FROM extraction_schema_versions "
                "WHERE document_type_id = :id AND is_active = true LIMIT 1"
            ),
            {"id": doc_type_id},
        ).first()

        version = _next_version(connection, "extraction_schema_versions", doc_type_id)
        new_schema_id = connection.execute(
            sa.text(
                "INSERT INTO extraction_schema_versions (document_type_id, version, is_active, notes) "
                "VALUES (:id, :version, false, :notes) RETURNING id"
            ),
            {"id": doc_type_id, "version": version, "notes": PVSYST_SCHEMA_NOTES},
        ).scalar_one()

        linked_field_ids: set[int] = set()
        max_priority = 0
        if active_schema:
            existing_links = connection.execute(
                sa.text(
                    "SELECT canonical_field_id, is_required, extraction_priority "
                    "FROM extraction_schema_version_fields WHERE schema_version_id = :s"
                ),
                {"s": active_schema[0]},
            ).fetchall()
            for canonical_field_id, is_required, extraction_priority in existing_links:
                make_required = bool(is_required) or canonical_field_id in baseline_field_ids
                connection.execute(
                    sa.text(
                        "INSERT INTO extraction_schema_version_fields "
                        "(schema_version_id, canonical_field_id, is_required, extraction_priority) "
                        "VALUES (:s, :c, :req, :p)"
                    ),
                    {
                        "s": new_schema_id,
                        "c": canonical_field_id,
                        "req": make_required,
                        "p": extraction_priority,
                    },
                )
                linked_field_ids.add(canonical_field_id)
                stats["fields_cloned"] += 1
                if canonical_field_id in baseline_field_ids:
                    stats["baseline_fields_marked_required"] += 1
                if extraction_priority is not None:
                    max_priority = max(max_priority, extraction_priority)

        # Guarantee every baseline-driving field is present (mark required).
        for canonical_field_id in baseline_field_ids:
            if canonical_field_id in linked_field_ids:
                continue
            max_priority += 10
            connection.execute(
                sa.text(
                    "INSERT INTO extraction_schema_version_fields "
                    "(schema_version_id, canonical_field_id, is_required, extraction_priority) "
                    "VALUES (:s, :c, true, :p)"
                ),
                {"s": new_schema_id, "c": canonical_field_id, "p": max_priority},
            )
            linked_field_ids.add(canonical_field_id)
            stats["baseline_fields_marked_required"] += 1

        # Flip activation: deactivate prior, activate v2.
        connection.execute(
            sa.text(
                "UPDATE extraction_schema_versions SET is_active = false WHERE document_type_id = :id"
            ),
            {"id": doc_type_id},
        )
        connection.execute(
            sa.text("UPDATE extraction_schema_versions SET is_active = true WHERE id = :id"),
            {"id": new_schema_id},
        )
        stats["schema_v2_created"] = True

    # --- Prompt v2 ---
    already_seeded_prompt = connection.execute(
        sa.text(
            "SELECT 1 FROM extraction_prompt_templates "
            "WHERE document_type_id = :id AND notes = :notes LIMIT 1"
        ),
        {"id": doc_type_id, "notes": PVSYST_PROMPT_NOTES},
    ).first()

    if not already_seeded_prompt:
        version = _next_version(connection, "extraction_prompt_templates", doc_type_id)
        new_prompt_id = connection.execute(
            sa.text(
                "INSERT INTO extraction_prompt_templates "
                "(document_type_id, version, is_active, system_prompt, extraction_prompt, "
                " model_name, temperature, max_tokens, notes) "
                "VALUES (:id, :version, false, :system_prompt, :extraction_prompt, "
                " :model_name, :temperature, :max_tokens, :notes) RETURNING id"
            ),
            {
                "id": doc_type_id,
                "version": version,
                "system_prompt": PVSYST_SYSTEM_PROMPT,
                "extraction_prompt": DEFAULT_EXTRACTION_PROMPT,
                "model_name": GENERIC_MODEL_NAME,
                "temperature": GENERIC_TEMPERATURE,
                "max_tokens": GENERIC_MAX_TOKENS,
                "notes": PVSYST_PROMPT_NOTES,
            },
        ).scalar_one()
        connection.execute(
            sa.text(
                "UPDATE extraction_prompt_templates SET is_active = false WHERE document_type_id = :id"
            ),
            {"id": doc_type_id},
        )
        connection.execute(
            sa.text("UPDATE extraction_prompt_templates SET is_active = true WHERE id = :id"),
            {"id": new_prompt_id},
        )
        stats["prompt_v2_created"] = True

    return stats


def remove_pvsyst_specialized_schema_v2(connection: Connection) -> dict:
    """Best-effort reversal of :func:`seed_pvsyst_specialized_schema_v2`.

    Deletes the marker-tagged v2 schema/prompt and reactivates the highest remaining
    (v1) schema/prompt so the doc type returns to its pre-Phase-1C active state.
    """
    stats = {"schema_v2_deleted": 0, "prompt_v2_deleted": 0}

    doc_type_row = connection.execute(
        sa.text("SELECT id FROM extraction_document_types WHERE name = :name"),
        {"name": PVSYST_DOC_TYPE_NAME},
    ).first()
    if not doc_type_row:
        return stats
    doc_type_id = doc_type_row[0]

    result = connection.execute(
        sa.text(
            "DELETE FROM extraction_schema_versions "
            "WHERE document_type_id = :id AND notes = :notes"
        ),
        {"id": doc_type_id, "notes": PVSYST_SCHEMA_NOTES},
    )
    stats["schema_v2_deleted"] = result.rowcount or 0

    result = connection.execute(
        sa.text(
            "DELETE FROM extraction_prompt_templates "
            "WHERE document_type_id = :id AND notes = :notes"
        ),
        {"id": doc_type_id, "notes": PVSYST_PROMPT_NOTES},
    )
    stats["prompt_v2_deleted"] = result.rowcount or 0

    # Reactivate the highest remaining (v1) schema/prompt.
    for table in ("extraction_schema_versions", "extraction_prompt_templates"):
        latest = connection.execute(
            sa.text(
                f"SELECT id FROM {table} WHERE document_type_id = :id ORDER BY version DESC LIMIT 1"
            ),
            {"id": doc_type_id},
        ).first()
        if latest:
            connection.execute(
                sa.text(f"UPDATE {table} SET is_active = false WHERE document_type_id = :id"),
                {"id": doc_type_id},
            )
            connection.execute(
                sa.text(f"UPDATE {table} SET is_active = true WHERE id = :id"),
                {"id": latest[0]},
            )

    return stats


def run() -> dict:
    """Standalone re-runnable entrypoint (outside Alembic)."""
    from app.db.session import SessionFactory

    session = SessionFactory()
    try:
        connection = session.connection()
        stats = seed_generic_extraction_coverage(connection)
        stats["pvsyst"] = seed_pvsyst_specialized_schema_v2(connection)
        session.commit()
        return stats
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print(run())

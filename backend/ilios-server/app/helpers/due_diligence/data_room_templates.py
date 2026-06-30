"""Data Room Templates helpers (Task #91).

A Data Room Template is a reusable, company-scoped snapshot of a Data Room's
*structure* — its stages/sections, the expected documents per section, their
ordering, descriptions, guidance and optionality. Structure only: never files,
versions, document metadata/keys, approvals or history.

This module is the single seam between a template's portable JSON ``structure``
and the canonical Data Room blueprint (``DocumentSections`` / ``SiteDocumentsEnum``):

  * ``snapshot_site_structure``        — read a site's live Data Room into a structure.
  * ``snapshot_default_structure``     — the canonical default blueprint as a structure.
  * ``validate_template_structure``    — fail-closed validation against the enums.
  * ``build_section_mappers_from_template`` — structure -> the two mappers the
    existing scaffolding helpers already accept.
  * ``apply_template_to_site``         — scaffold a site's Data Room from a structure
    by REUSING the existing creation path (no parallel scaffolding logic).
  * ``serialize_template`` / ``parse_imported_template`` — portable export/import.

Applying a template never creates placeholder ``File`` rows; it only creates the
section and expected-document slots, exactly like the default site-creation path.
The canonical ``Site`` entity is untouched (Project == Site is a UI label only).
"""
from __future__ import annotations

import csv
import io
from typing import Any

from sqlalchemy.orm import Session

from app.crud.document import DocumentCRUD
from app.crud.document_section import DocumentSectionCRUD
from app.helpers.due_diligence.document_section_mapper import (
    document_name_section_mapper,
    document_sub_sections_mapper,
)
from app.helpers.due_diligence.due_diligence_helper import (
    create_default_site_document_sections,
    generate_default_site_documents,
)
from app.helpers.due_diligence.expected_documents import EXPECTED_DOCUMENT_OVERRIDES
from app.static.default_site_documents_enum import DocumentSections, SiteDocumentsEnum

STRUCTURE_VERSION = 1
EXPORT_FORMAT = "ilios.data_room_template"
EXPORT_VERSION = 1

# Enum key -> member lookups (keys are the stable enum member NAMES, e.g. "stage1",
# "site_lease"). These are the portable identifiers stored in a template.
_SECTION_BY_KEY: dict[str, DocumentSections] = {s.name: s for s in DocumentSections}
_DOCUMENT_BY_KEY: dict[str, SiteDocumentsEnum] = {d.name: d for d in SiteDocumentsEnum}


class TemplateStructureError(ValueError):
    """Raised when a template structure fails validation."""


def _document_node(kind: SiteDocumentsEnum, description: str | None = None) -> dict[str, Any]:
    override = EXPECTED_DOCUMENT_OVERRIDES.get(kind, {})
    return {
        "kind": kind.name,
        "description": description if description is not None else override.get("description"),
        "guidance": override.get("description"),
        "required": override.get("required", True),
    }


def snapshot_default_structure() -> dict[str, Any]:
    """Return the canonical default Data Room blueprint as a template structure."""
    sections: list[dict[str, Any]] = []
    for top_section in document_sub_sections_mapper:
        sub_keys = document_sub_sections_mapper.get(top_section, [])
        sections.append(
            {
                "key": top_section.name,
                "documents": [
                    _document_node(doc) for doc in document_name_section_mapper.get(top_section, [])
                ],
                "subsections": [
                    {
                        "key": sub.name,
                        "documents": [
                            _document_node(doc) for doc in document_name_section_mapper.get(sub, [])
                        ],
                    }
                    for sub in sub_keys
                ],
            }
        )
    return {"version": STRUCTURE_VERSION, "sections": sections}


def snapshot_site_structure(site_id: int, db_session: Session) -> dict[str, Any]:
    """Snapshot a site's *current* Data Room structure into a template structure.

    Only enum-kinded, non-archived documents are captured (custom one-off documents
    have no portable enum kind and are intentionally skipped). Ordering follows the
    live ``position`` of sections and documents. Descriptions are taken from the
    live document rows; guidance/optionality fall back to the expected-documents
    catalog. No file/version/metadata/approval/history state is read.
    """
    sections = DocumentSectionCRUD(db_session).get_site_sections(site_id)

    # Build parent -> ordered children and a per-section ordered document list.
    by_id = {section.id: section for section in sections}
    children: dict[int, list] = {}
    top_level: list = []
    for section in sections:
        if section.parent_section_id is None:
            top_level.append(section)
        else:
            children.setdefault(section.parent_section_id, []).append(section)

    top_level.sort(key=lambda s: (s.position or 0, s.id))
    for child_list in children.values():
        child_list.sort(key=lambda s: (s.position or 0, s.id))

    def _docs_for(section) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        ordered_docs = sorted(
            section.documents, key=lambda d: (d.position or 0, d.id)
        )
        for doc in ordered_docs:
            if doc.is_archived or doc.name is None:
                continue
            nodes.append(_document_node(doc.name, description=doc.description))
        return nodes

    out_sections: list[dict[str, Any]] = []
    for top in top_level:
        if top.name is None:
            continue
        out_sections.append(
            {
                "key": top.name.name,
                "documents": _docs_for(top),
                "subsections": [
                    {"key": child.name.name, "documents": _docs_for(child)}
                    for child in children.get(top.id, [])
                    if child.name is not None
                ],
            }
        )
    return {"version": STRUCTURE_VERSION, "sections": out_sections}


def validate_template_structure(structure: Any) -> dict[str, Any]:
    """Validate (and lightly normalize) a template structure. Fail-closed.

    Returns a normalized structure on success; raises ``TemplateStructureError``
    with a human-readable message otherwise. Every section/subsection key must be a
    known ``DocumentSections`` member and every document kind a known
    ``SiteDocumentsEnum`` member.
    """
    if not isinstance(structure, dict):
        raise TemplateStructureError("Template structure must be an object.")

    raw_sections = structure.get("sections")
    if not isinstance(raw_sections, list) or not raw_sections:
        raise TemplateStructureError("Template structure must contain a non-empty 'sections' list.")

    seen_section_keys: set[str] = set()
    norm_sections: list[dict[str, Any]] = []

    def _norm_documents(raw_docs: Any, where: str) -> list[dict[str, Any]]:
        if raw_docs is None:
            return []
        if not isinstance(raw_docs, list):
            raise TemplateStructureError(f"'documents' under {where} must be a list.")
        out: list[dict[str, Any]] = []
        seen_kinds: set[str] = set()
        for doc in raw_docs:
            if not isinstance(doc, dict):
                raise TemplateStructureError(f"Each document under {where} must be an object.")
            kind = doc.get("kind")
            if kind not in _DOCUMENT_BY_KEY:
                raise TemplateStructureError(f"Unknown document kind '{kind}' under {where}.")
            if kind in seen_kinds:
                raise TemplateStructureError(f"Duplicate document kind '{kind}' under {where}.")
            seen_kinds.add(kind)
            description = doc.get("description")
            guidance = doc.get("guidance")
            required = doc.get("required", True)
            if description is not None and not isinstance(description, str):
                raise TemplateStructureError(f"Document '{kind}' description must be a string.")
            if guidance is not None and not isinstance(guidance, str):
                raise TemplateStructureError(f"Document '{kind}' guidance must be a string.")
            if not isinstance(required, bool):
                raise TemplateStructureError(f"Document '{kind}' required must be a boolean.")
            out.append(
                {
                    "kind": kind,
                    "description": description,
                    "guidance": guidance,
                    "required": required,
                }
            )
        return out

    for section in raw_sections:
        if not isinstance(section, dict):
            raise TemplateStructureError("Each section must be an object.")
        key = section.get("key")
        if key not in _SECTION_BY_KEY:
            raise TemplateStructureError(f"Unknown section key '{key}'.")
        if key in seen_section_keys:
            raise TemplateStructureError(f"Duplicate section key '{key}'.")
        seen_section_keys.add(key)

        raw_subs = section.get("subsections") or []
        if not isinstance(raw_subs, list):
            raise TemplateStructureError(f"'subsections' under section '{key}' must be a list.")
        norm_subs: list[dict[str, Any]] = []
        for sub in raw_subs:
            if not isinstance(sub, dict):
                raise TemplateStructureError(f"Each subsection under '{key}' must be an object.")
            sub_key = sub.get("key")
            if sub_key not in _SECTION_BY_KEY:
                raise TemplateStructureError(f"Unknown subsection key '{sub_key}' under '{key}'.")
            if sub_key in seen_section_keys:
                raise TemplateStructureError(f"Duplicate section key '{sub_key}'.")
            seen_section_keys.add(sub_key)
            norm_subs.append(
                {"key": sub_key, "documents": _norm_documents(sub.get("documents"), f"subsection '{sub_key}'")}
            )

        norm_sections.append(
            {
                "key": key,
                "documents": _norm_documents(section.get("documents"), f"section '{key}'"),
                "subsections": norm_subs,
            }
        )

    return {"version": STRUCTURE_VERSION, "sections": norm_sections}


def build_section_mappers_from_template(structure: dict[str, Any]):
    """Translate a (validated) structure into the two mappers the existing scaffolding
    helpers already accept.

    Returns a tuple ``(sub_sections_mapper, document_mapper, descriptions)`` where:
      * ``sub_sections_mapper`` = {top DocumentSections: [sub DocumentSections, ...]}
      * ``document_mapper``     = {DocumentSections: [SiteDocumentsEnum, ...]}
      * ``descriptions``        = {(section_key, kind): description or None}

    Insertion order is preserved so the existing ``enumerate``-based positioning in
    the scaffolding helpers reproduces the template ordering exactly.
    """
    sub_sections_mapper: dict[DocumentSections, list[DocumentSections]] = {}
    document_mapper: dict[DocumentSections, list[SiteDocumentsEnum]] = {}
    descriptions: dict[tuple[str, str], str | None] = {}

    for section in structure["sections"]:
        section_enum = _SECTION_BY_KEY[section["key"]]
        sub_enums = [_SECTION_BY_KEY[sub["key"]] for sub in section.get("subsections", [])]
        sub_sections_mapper[section_enum] = sub_enums

        section_docs = section.get("documents", [])
        if section_docs:
            document_mapper[section_enum] = [_DOCUMENT_BY_KEY[d["kind"]] for d in section_docs]
            for d in section_docs:
                descriptions[(section["key"], d["kind"])] = d.get("description")

        for sub in section.get("subsections", []):
            sub_enum = _SECTION_BY_KEY[sub["key"]]
            sub_docs = sub.get("documents", [])
            if sub_docs:
                document_mapper[sub_enum] = [_DOCUMENT_BY_KEY[d["kind"]] for d in sub_docs]
                for d in sub_docs:
                    descriptions[(sub["key"], d["kind"])] = d.get("description")

    return sub_sections_mapper, document_mapper, descriptions


def apply_template_to_site(site_id: int, structure: dict[str, Any], db_session: Session) -> None:
    """Scaffold ``site_id``'s Data Room from a template structure.

    Reuses the existing creation path: it builds the same two mappers the default
    flow uses and calls the very same scaffolding helpers, then enriches the
    generated document payloads with the template's descriptions before insert.
    No File rows are created.
    """
    structure = validate_template_structure(structure)
    sub_sections_mapper, document_mapper, descriptions = build_section_mappers_from_template(structure)

    create_default_site_document_sections([site_id], db_session, sub_sections_mapper=sub_sections_mapper)

    # Map freshly created section ids back to their enum key so descriptions can be
    # attached to the right (section, kind) document payload.
    section_id_to_key = {
        section.id: section.name.name
        for section in DocumentSectionCRUD(db_session).get_site_sections(site_id)
        if section.name is not None
    }

    payloads = generate_default_site_documents([site_id], db_session, document_mapper=document_mapper)
    for payload in payloads:
        section_key = section_id_to_key.get(payload.get("section_id"))
        # payload["name"] is the SiteDocumentsEnum member name (the stable kind).
        description = descriptions.get((section_key, payload.get("name")))
        if description is not None:
            payload["description"] = description

    DocumentCRUD(db_session).create_items(payloads)


def serialize_template(template) -> dict[str, Any]:
    """Build a portable, self-describing export payload for a template row."""
    return {
        "format": EXPORT_FORMAT,
        "export_version": EXPORT_VERSION,
        "name": template.name,
        "description": template.description,
        "structure": template.structure,
    }


def parse_imported_template(payload: Any) -> dict[str, Any]:
    """Validate an imported export payload and return ``{name, description, structure}``.

    Accepts either a full export envelope (with ``format``/``structure``) or a bare
    structure object. Fail-closed via ``validate_template_structure``.
    """
    if not isinstance(payload, dict):
        raise TemplateStructureError("Imported template must be a JSON object.")

    if "structure" in payload:
        name = payload.get("name") or "Imported Template"
        description = payload.get("description")
        structure = payload.get("structure")
    elif "sections" in payload:
        name = payload.get("name") or "Imported Template"
        description = payload.get("description")
        structure = payload
    else:
        raise TemplateStructureError("Imported template is missing a 'structure'.")

    if not isinstance(name, str) or not name.strip():
        raise TemplateStructureError("Imported template name must be a non-empty string.")
    if description is not None and not isinstance(description, str):
        raise TemplateStructureError("Imported template description must be a string.")

    structure = validate_template_structure(structure)
    return {"name": name.strip(), "description": description, "structure": structure}


# --- CSV import -------------------------------------------------------------
# A flat, spreadsheet-friendly alternative to the JSON envelope: one row per
# expected document. Sections/subsections are created in first-appearance order
# and the assembled structure is validated fail-closed exactly like JSON import.
CSV_COLUMNS = ("section_key", "subsection_key", "kind", "description", "guidance", "required")
CSV_REQUIRED_COLUMNS = ("section_key", "kind")
_CSV_TRUE_VALUES = {"true", "t", "1", "yes", "y", "required"}
_CSV_FALSE_VALUES = {"false", "f", "0", "no", "n", "optional"}


def _parse_csv_required(raw: str | None, *, kind: str, row_num: int) -> bool:
    if raw is None or not raw.strip():
        return True
    value = raw.strip().lower()
    if value in _CSV_TRUE_VALUES:
        return True
    if value in _CSV_FALSE_VALUES:
        return False
    raise TemplateStructureError(
        f"Row {row_num}: 'required' for '{kind}' must be true/false (got '{raw.strip()}')."
    )


def parse_csv_template(csv_text: Any) -> dict[str, Any]:
    """Parse a flat CSV (one row per expected document) into a validated structure.

    Header row required (case-insensitive). Recognized columns:
      * ``section_key``    (required) — stable DocumentSections member key
      * ``subsection_key`` (optional) — nests the document under a subsection
      * ``kind``           (required to add a document) — stable SiteDocumentsEnum key
      * ``description``    (optional)
      * ``guidance``       (optional)
      * ``required``       (optional, true/false, defaults to true)

    Sections and subsections are created in first-appearance order. A row with a
    blank ``kind`` registers an (empty) section/subsection without a document.
    Unknown keys/kinds and duplicates are rejected fail-closed by
    ``validate_template_structure`` — identical guarantees to JSON import.
    """
    if not isinstance(csv_text, str):
        raise TemplateStructureError("CSV import is empty.")
    # Strip a leading UTF-8 BOM (Excel/Sheets exports commonly prefix one).
    if csv_text.startswith("\ufeff"):
        csv_text = csv_text[1:]
    if not csv_text.strip():
        raise TemplateStructureError("CSV import is empty.")

    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise TemplateStructureError("CSV import is missing a header row.")

    header = {(name or "").strip().lower() for name in reader.fieldnames}
    missing = [column for column in CSV_REQUIRED_COLUMNS if column not in header]
    if missing:
        raise TemplateStructureError(
            "CSV header must include the column(s): " + ", ".join(missing) + "."
        )

    def _cell(row: dict[str, Any], column: str) -> str | None:
        for key, value in row.items():
            if isinstance(key, str) and key.strip().lower() == column:
                return value if isinstance(value, str) else None
        return None

    sections: dict[str, dict[str, Any]] = {}
    has_data_row = False

    for row_num, row in enumerate(reader, start=2):  # row 1 is the header
        cells = {column: _cell(row, column) for column in CSV_COLUMNS}
        if not any((value or "").strip() for value in cells.values()):
            continue  # skip fully blank lines
        has_data_row = True

        section_key = (cells["section_key"] or "").strip()
        if not section_key:
            raise TemplateStructureError(f"Row {row_num}: 'section_key' is required.")

        subsection_key = (cells["subsection_key"] or "").strip() or None
        kind = (cells["kind"] or "").strip() or None
        description = (cells["description"] or "").strip() or None
        guidance = (cells["guidance"] or "").strip() or None

        section = sections.setdefault(
            section_key, {"key": section_key, "documents": [], "subsections": {}}
        )
        if subsection_key:
            subsection = section["subsections"].setdefault(
                subsection_key, {"key": subsection_key, "documents": []}
            )
            target_documents = subsection["documents"]
        else:
            target_documents = section["documents"]

        if kind:
            target_documents.append(
                {
                    "kind": kind,
                    "description": description,
                    "guidance": guidance,
                    "required": _parse_csv_required(cells["required"], kind=kind, row_num=row_num),
                }
            )

    if not has_data_row:
        raise TemplateStructureError("CSV import has no data rows.")

    structure = {
        "version": STRUCTURE_VERSION,
        "sections": [
            {
                "key": section["key"],
                "documents": section["documents"],
                "subsections": [
                    {"key": sub["key"], "documents": sub["documents"]}
                    for sub in section["subsections"].values()
                ],
            }
            for section in sections.values()
        ],
    }
    return validate_template_structure(structure)

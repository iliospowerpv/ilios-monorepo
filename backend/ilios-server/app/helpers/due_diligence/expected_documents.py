"""Expected Documents definition (Task #90).

A per-stage / per-section, read-only definition of the documents that are expected
to exist in a Data Room. It is layered additively over the existing
``DocumentSections`` / ``SiteDocumentsEnum`` structure (via
``document_name_section_mapper``) and is purely declarative:

  * It NEVER creates placeholder ``Document`` or ``File`` rows.
  * It does NOT alter sectioning, versioning, promotion, archive or move-stage.
  * It is the foundation later phases (templates, guided upload, the guidance
    dashboard, AI awareness) build on.

Each expected document exposes:
  - ``kind``        : stable enum key (e.g. ``"site_lease"``)
  - ``name``        : human-readable name (the ``SiteDocumentsEnum`` value)
  - ``description`` : optional guidance text (``None`` unless overridden)
  - ``required``    : whether the document is required (default ``True`` — these
                      are due-diligence requirements) or optional
  - ``position``    : 1-indexed ordering within its section (mirrors the mapper)

Per-document optionality and descriptions can be tuned via
``EXPECTED_DOCUMENT_OVERRIDES`` without re-listing the full catalog.
"""
from __future__ import annotations

from app.helpers.due_diligence.document_section_mapper import document_name_section_mapper
from app.static.default_site_documents_enum import DocumentSections, SiteDocumentsEnum

# Overrides keyed by SiteDocumentsEnum member. Anything not listed defaults to
# required=True and description=None. Keep this conservative and additive — it is
# guidance metadata only and changes no behaviour.
EXPECTED_DOCUMENT_OVERRIDES: dict[SiteDocumentsEnum, dict] = {
    SiteDocumentsEnum.executive_summary: {
        "required": False,
        "description": "High-level narrative summary of the investment opportunity.",
    },
    SiteDocumentsEnum.project_preview: {
        "required": False,
        "description": "Preliminary project overview used for early screening.",
    },
    SiteDocumentsEnum.org_chart_before_after_investment: {
        "description": "Ownership / org structure before and after the investment closes.",
    },
    SiteDocumentsEnum.site_lease: {
        "description": "Executed lease for the project site land.",
    },
    SiteDocumentsEnum.ppa_and_amendments: {
        "description": "Power Purchase Agreement and all executed amendments.",
    },
    SiteDocumentsEnum.epc_agreement: {
        "description": "Engineering, Procurement & Construction agreement.",
    },
    SiteDocumentsEnum.om_agreement: {
        "description": "Operations & Maintenance and production-guarantee agreement.",
    },
    SiteDocumentsEnum.interconnection_agreement_and_amendments: {
        "description": "Utility interconnection agreement and amendments.",
    },
    SiteDocumentsEnum.permission_to_operate_pto: {
        "description": "Utility Permission to Operate authorization.",
    },
    SiteDocumentsEnum.commercial_operation_date_cod: {
        "description": "Evidence of the Commercial Operation Date.",
    },
}


def _build_expected_document(section_document: SiteDocumentsEnum, position: int) -> dict:
    override = EXPECTED_DOCUMENT_OVERRIDES.get(section_document, {})
    return {
        "kind": section_document.name,
        "name": section_document.value,
        "description": override.get("description"),
        "required": override.get("required", True),
        "position": position,
    }


def get_expected_documents_for_section(section: DocumentSections) -> list[dict]:
    """Return the ordered expected documents for a single section enum."""
    section_documents = document_name_section_mapper.get(section, [])
    return [
        _build_expected_document(section_document, position)
        for position, section_document in enumerate(section_documents, start=1)
    ]


def get_expected_documents_by_section() -> dict[DocumentSections, list[dict]]:
    """Return expected documents keyed by every section that defines any."""
    return {
        section: get_expected_documents_for_section(section)
        for section in document_name_section_mapper
    }

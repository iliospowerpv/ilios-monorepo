"""Real-shape contract guard for the AI Assistant's Data Room read tools (Task #108).

Unlike ``tests/test_assistant_phase2.py`` — which exercises the tool layer against FAKE services and
therefore CANNOT notice when a wrapped read service changes shape — these tests run the REAL catalog
and guidance code and assert the exact output keys each of the four Data Room assistant tools (and
the #107 deep link) depend on:

  * ``get_site_expected_documents`` / the deep link read each expected-document's
    ``kind``/``name``/``description``/``required``/``position``.
  * ``get_site_data_room_guidance`` passes through each stage item AND its NESTED
    ``missing_documents`` (the #107 deep link keys off ``missing_documents[].kind``).
  * ``get_site_data_room_documents`` / ``get_site_data_room_templates`` read specific ORM attributes.

If any of these drift (a key disappears, ``missing_documents`` moves back to the top level, or a
Document/Template attribute is renamed) these tests fail LOUDLY — before the assistant silently
returns broken answers. DB-free: only the thin CRUD seams are stubbed; no live rows are required.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.helpers.due_diligence.expected_documents import get_expected_documents_for_section
from app.models.data_room_template import DataRoomTemplate
from app.models.document import Document
from app.services.due_diligence import data_room_guidance_service as guidance_module
from app.services.due_diligence.data_room_guidance_service import DataRoomGuidanceService
from app.static.default_site_documents_enum import DocumentSections

# Keys the assistant surfaces per expected document (tools._t_get_site_expected_documents copies the
# catalog dicts verbatim) AND that the #107 deep link reads (``kind``).
_EXPECTED_DOCUMENT_KEYS = {"kind", "name", "description", "required", "position"}

# Keys tools._t_get_site_data_room_guidance passes through per stage item.
_GUIDANCE_STAGE_KEYS = {
    "section_id",
    "section_key",
    "section_name",
    "expected",
    "present",
    "missing",
    "needs_update",
    "optional",
    "archived",
    "version_count",
    "promotion_status",
    "missing_documents",
}


def test_expected_documents_catalog_exposes_the_keys_the_tool_reads():
    """The static catalog must expose every key the assistant tool/deep-link reads, for every doc."""
    seen_any = False
    for section in DocumentSections:
        for doc in get_expected_documents_for_section(section):
            seen_any = True
            assert _EXPECTED_DOCUMENT_KEYS <= set(doc), (
                f"expected-document dict for {section!r} is missing keys: "
                f"{_EXPECTED_DOCUMENT_KEYS - set(doc)}"
            )
    assert seen_any, "catalog produced no expected documents — the tool would always be empty"


def _patch_sections(monkeypatch, sections):
    """Stub the ONLY DB seam build_guidance uses (DocumentSectionCRUD.get_site_sections)."""

    class _FakeSectionCRUD:
        def __init__(self, _db):
            pass

        def get_site_sections(self, _site_id):
            return list(sections)

    monkeypatch.setattr(guidance_module, "DocumentSectionCRUD", _FakeSectionCRUD)


def test_guidance_nests_missing_documents_per_stage(monkeypatch):
    """The REAL guidance service must keep ``missing_documents`` NESTED inside each stage item.

    With no live sections, every catalog stage is fully missing — enough to assert the nested shape
    and per-entry keys without a database. (The phase2 fake once wrongly put ``missing_documents`` at
    the TOP level; this guards against any code drifting back to that broken shape.)
    """
    _patch_sections(monkeypatch, [])

    result = DataRoomGuidanceService(MagicMock(name="db")).build_guidance(1)

    assert set(result) == {"items"}, "guidance must NOT expose a top-level missing_documents key"
    assert result["items"], "expected at least one stage that defines expected documents"
    for item in result["items"]:
        assert _GUIDANCE_STAGE_KEYS <= set(item), (
            f"stage item missing keys: {_GUIDANCE_STAGE_KEYS - set(item)}"
        )
        assert isinstance(item["missing_documents"], list)
        for doc in item["missing_documents"]:
            # The #107 deep link keys off ``kind``; the panel/dialog display ``name``.
            assert "kind" in doc and "name" in doc


def test_guidance_present_split_reads_real_document_attributes(monkeypatch):
    """Exercise the present/missing split over REAL Document attribute names.

    A present identity (>=1 file version, not archived) must drop out of ``missing_documents``. This
    fails if ``identity_kind`` / ``files_count`` / ``is_archived`` are renamed on the guidance path.
    """
    stage = next(s for s in DocumentSections if get_expected_documents_for_section(s))
    present_kind = get_expected_documents_for_section(stage)[0]["kind"]

    present_doc = SimpleNamespace(
        identity_kind=present_kind,
        files_count=2,
        is_archived=False,
        assumption_promotions=[],
        files=[SimpleNamespace(version_number=1, deleted=False)],
    )
    section_row = SimpleNamespace(
        id=99,
        name=SimpleNamespace(name=stage.name, value=stage.value),
        documents=[present_doc],
    )
    _patch_sections(monkeypatch, [section_row])

    result = DataRoomGuidanceService(MagicMock(name="db")).build_guidance(1)
    item = next(it for it in result["items"] if it["section_key"] == stage.name)

    assert item["section_id"] == 99
    assert present_kind not in {doc["kind"] for doc in item["missing_documents"]}
    assert item["present"] >= 1


def test_document_model_exposes_attributes_the_documents_tool_reads():
    """get_site_data_room_documents reads these Document attributes — guard against renames."""
    for attr in (
        "id",
        "identity_name",
        "identity_kind",
        "identity_aliases",
        "section_id",
        "section",
        "is_archived",
        "files_count",
        "files",
    ):
        assert hasattr(Document, attr), f"Document.{attr} missing — the documents tool would break"


def test_template_model_exposes_attributes_the_templates_tool_reads():
    """get_site_data_room_templates reads these DataRoomTemplate attributes — guard against renames."""
    for attr in ("id", "name", "description", "is_archived", "structure"):
        assert hasattr(
            DataRoomTemplate, attr
        ), f"DataRoomTemplate.{attr} missing — the templates tool would break"

"""Tests for Data Room Templates (Task #91).

Covers the helper (snapshot / validate / build-mappers / apply / import-export),
the company-scoped CRUD guard, and the router (CRUD + authz + import/export +
cross-company isolation). The canonical ``Site`` entity is never mutated by a
template; applying one only scaffolds sections + expected-document slots through
the existing creation path (no File rows).
"""
import asyncio
from unittest.mock import Mock

import pytest

from app.crud.company import CompanyCRUD
from app.crud.data_room_template import DataRoomTemplateCRUD
from app.crud.document_section import DocumentSectionCRUD
from app.helpers.due_diligence import data_room_templates as drt
from app.helpers.due_diligence.data_room_templates import (
    TemplateStructureError,
    apply_template_to_site,
    build_section_mappers_from_template,
    parse_csv_template,
    parse_imported_template,
    serialize_template,
    snapshot_default_structure,
    snapshot_site_structure,
    validate_template_structure,
)
from app.routers.due_diligence import document_templates as router_mod
from app.static.companies import CompanyTypes
from app.static.default_site_documents_enum import DocumentSections, SiteDocumentsEnum


def _sample_structure() -> dict:
    """A small, valid two-section structure built from real enum members."""
    return {
        "version": 1,
        "sections": [
            {
                "key": DocumentSections.executive_summary.name,
                "documents": [
                    {
                        "kind": SiteDocumentsEnum.executive_summary.name,
                        "description": "Investment thesis overview.",
                        "guidance": None,
                        "required": True,
                    }
                ],
                "subsections": [],
            },
            {
                "key": DocumentSections.preview.name,
                "documents": [
                    {
                        "kind": SiteDocumentsEnum.site_lease.name,
                        "description": "Executed site lease.",
                        "guidance": None,
                        "required": False,
                    },
                    {
                        "kind": SiteDocumentsEnum.ppa_and_amendments.name,
                        "description": None,
                        "guidance": None,
                        "required": True,
                    },
                ],
                "subsections": [],
            },
        ],
    }


class TestValidateTemplateStructure:
    def test_accepts_default_structure(self):
        normalized = validate_template_structure(snapshot_default_structure())
        assert normalized["sections"]

    def test_accepts_sample_structure(self):
        normalized = validate_template_structure(_sample_structure())
        assert len(normalized["sections"]) == 2

    def test_rejects_non_dict(self):
        with pytest.raises(TemplateStructureError):
            validate_template_structure(["not", "a", "dict"])

    def test_rejects_empty_sections(self):
        with pytest.raises(TemplateStructureError):
            validate_template_structure({"version": 1, "sections": []})

    def test_rejects_unknown_section_key(self):
        with pytest.raises(TemplateStructureError):
            validate_template_structure({"sections": [{"key": "__nope__", "documents": []}]})

    def test_rejects_unknown_document_kind(self):
        structure = {
            "sections": [
                {
                    "key": DocumentSections.preview.name,
                    "documents": [{"kind": "__nope__"}],
                }
            ]
        }
        with pytest.raises(TemplateStructureError):
            validate_template_structure(structure)

    def test_rejects_duplicate_section_key(self):
        structure = {
            "sections": [
                {"key": DocumentSections.preview.name, "documents": []},
                {"key": DocumentSections.preview.name, "documents": []},
            ]
        }
        with pytest.raises(TemplateStructureError):
            validate_template_structure(structure)

    def test_rejects_duplicate_document_kind(self):
        structure = {
            "sections": [
                {
                    "key": DocumentSections.preview.name,
                    "documents": [
                        {"kind": SiteDocumentsEnum.site_lease.name},
                        {"kind": SiteDocumentsEnum.site_lease.name},
                    ],
                }
            ]
        }
        with pytest.raises(TemplateStructureError):
            validate_template_structure(structure)

    def test_rejects_non_bool_required(self):
        structure = {
            "sections": [
                {
                    "key": DocumentSections.preview.name,
                    "documents": [{"kind": SiteDocumentsEnum.site_lease.name, "required": "yes"}],
                }
            ]
        }
        with pytest.raises(TemplateStructureError):
            validate_template_structure(structure)


class TestSnapshotAndMappers:
    def test_default_structure_has_documents(self):
        structure = snapshot_default_structure()
        total_docs = sum(
            len(s.get("documents", [])) + sum(len(sub.get("documents", [])) for sub in s.get("subsections", []))
            for s in structure["sections"]
        )
        assert total_docs > 0

    def test_build_mappers_preserves_order(self):
        structure = validate_template_structure(_sample_structure())
        sub_sections_mapper, document_mapper, descriptions = build_section_mappers_from_template(structure)

        assert DocumentSections.executive_summary in sub_sections_mapper
        assert document_mapper[DocumentSections.preview] == [
            SiteDocumentsEnum.site_lease,
            SiteDocumentsEnum.ppa_and_amendments,
        ]
        assert descriptions[(DocumentSections.preview.name, SiteDocumentsEnum.site_lease.name)] == "Executed site lease."


class TestImportExport:
    def test_serialize_template_envelope(self):
        template = Mock()
        template.name = "T"
        template.description = "d"
        template.structure = _sample_structure()
        payload = serialize_template(template)
        assert payload["format"] == drt.EXPORT_FORMAT
        assert payload["structure"] == _sample_structure()

    def test_parse_envelope_roundtrip(self):
        template = Mock()
        template.name = "Exported"
        template.description = "desc"
        template.structure = _sample_structure()
        envelope = serialize_template(template)
        parsed = parse_imported_template(envelope)
        assert parsed["name"] == "Exported"
        assert parsed["description"] == "desc"
        assert len(parsed["structure"]["sections"]) == 2

    def test_parse_bare_structure(self):
        parsed = parse_imported_template(_sample_structure())
        assert parsed["name"] == "Imported Template"
        assert parsed["structure"]["sections"]

    def test_parse_rejects_missing_structure(self):
        with pytest.raises(TemplateStructureError):
            parse_imported_template({"name": "x"})

    def test_parse_rejects_non_dict(self):
        with pytest.raises(TemplateStructureError):
            parse_imported_template("nope")


class TestCsvImport:
    def test_parse_minimal_csv(self):
        csv_text = (
            "section_key,subsection_key,kind,description,guidance,required\n"
            f"{DocumentSections.executive_summary.name},,{SiteDocumentsEnum.executive_summary.name},Thesis,,true\n"
            f"{DocumentSections.preview.name},,{SiteDocumentsEnum.site_lease.name},Lease,,false\n"
        )
        structure = parse_csv_template(csv_text)
        keys = [s["key"] for s in structure["sections"]]
        # Sections are created in first-appearance order.
        assert keys == [DocumentSections.executive_summary.name, DocumentSections.preview.name]
        lease = structure["sections"][1]["documents"][0]
        assert lease["kind"] == SiteDocumentsEnum.site_lease.name
        assert lease["description"] == "Lease"
        assert lease["required"] is False

    def test_groups_documents_under_subsection(self):
        secs = list(DocumentSections)
        docs = list(SiteDocumentsEnum)
        section_key, sub_key, doc_kind = secs[0].name, secs[1].name, docs[0].name
        csv_text = (
            "section_key,subsection_key,kind,description,guidance,required\n"
            f"{section_key},{sub_key},{doc_kind},Sub doc,Upload it,true\n"
        )
        structure = parse_csv_template(csv_text)
        section = structure["sections"][0]
        assert section["documents"] == []
        assert section["subsections"][0]["key"] == sub_key
        assert section["subsections"][0]["documents"][0]["kind"] == doc_kind

    def test_required_defaults_true_and_accepts_variants(self):
        csv_text = (
            "section_key,kind,required\n"
            f"{DocumentSections.preview.name},{SiteDocumentsEnum.site_lease.name},\n"
            f"{DocumentSections.preview.name},{SiteDocumentsEnum.ppa_and_amendments.name},no\n"
        )
        docs = parse_csv_template(csv_text)["sections"][0]["documents"]
        assert docs[0]["required"] is True  # blank -> default true
        assert docs[1]["required"] is False  # "no" -> false

    def test_header_is_case_insensitive_and_skips_blank_rows(self):
        csv_text = (
            "Section_Key, Kind ,Required\n"
            "\n"
            f"{DocumentSections.preview.name},{SiteDocumentsEnum.site_lease.name},yes\n"
        )
        structure = parse_csv_template(csv_text)
        assert structure["sections"][0]["documents"][0]["kind"] == SiteDocumentsEnum.site_lease.name

    def test_strips_utf8_bom_header(self):
        csv_text = (
            "\ufeffsection_key,kind,required\n"
            f"{DocumentSections.preview.name},{SiteDocumentsEnum.site_lease.name},true\n"
        )
        structure = parse_csv_template(csv_text)
        assert structure["sections"][0]["documents"][0]["kind"] == SiteDocumentsEnum.site_lease.name

    def test_rejects_missing_required_column(self):
        with pytest.raises(TemplateStructureError):
            parse_csv_template("section_key,description\nstage1,foo\n")

    def test_rejects_unknown_section_key(self):
        with pytest.raises(TemplateStructureError):
            parse_csv_template(f"section_key,kind\n__nope__,{SiteDocumentsEnum.site_lease.name}\n")

    def test_rejects_unknown_document_kind(self):
        with pytest.raises(TemplateStructureError):
            parse_csv_template(f"section_key,kind\n{DocumentSections.preview.name},__nope__\n")

    def test_rejects_invalid_required_value(self):
        csv_text = (
            "section_key,kind,required\n"
            f"{DocumentSections.preview.name},{SiteDocumentsEnum.site_lease.name},maybe\n"
        )
        with pytest.raises(TemplateStructureError):
            parse_csv_template(csv_text)

    def test_rejects_empty_csv(self):
        with pytest.raises(TemplateStructureError):
            parse_csv_template("   ")

    def test_rejects_header_only_csv(self):
        with pytest.raises(TemplateStructureError):
            parse_csv_template("section_key,kind\n")

    def test_rejects_duplicate_kind_in_same_section(self):
        csv_text = (
            "section_key,kind\n"
            f"{DocumentSections.preview.name},{SiteDocumentsEnum.site_lease.name}\n"
            f"{DocumentSections.preview.name},{SiteDocumentsEnum.site_lease.name}\n"
        )
        with pytest.raises(TemplateStructureError):
            parse_csv_template(csv_text)


class TestImportSchemaValidation:
    def test_requires_exactly_one_source(self):
        from pydantic import ValidationError

        from app.schema.data_room_templates import ImportTemplateSchema

        with pytest.raises(ValidationError):
            ImportTemplateSchema()  # neither payload nor csv
        with pytest.raises(ValidationError):
            ImportTemplateSchema(payload={"sections": []}, csv="x")  # both
        # Exactly one source is accepted (structure validity is checked later).
        assert ImportTemplateSchema(csv="x").csv == "x"
        assert ImportTemplateSchema(payload={"sections": []}).payload == {"sections": []}


class TestApplyAndSnapshotRoundTrip:
    def test_apply_template_creates_sections_and_documents(self, db_session, site):
        apply_template_to_site(site.id, _sample_structure(), db_session)
        db_session.commit()

        sections = DocumentSectionCRUD(db_session).get_site_sections(site.id)
        section_names = {s.name.name for s in sections if s.name is not None}
        assert DocumentSections.executive_summary.name in section_names
        assert DocumentSections.preview.name in section_names

        doc_names = {d.name.name for s in sections for d in s.documents if d.name is not None}
        assert SiteDocumentsEnum.site_lease.name in doc_names
        assert SiteDocumentsEnum.ppa_and_amendments.name in doc_names

    def test_snapshot_after_apply_roundtrips(self, db_session, site):
        apply_template_to_site(site.id, _sample_structure(), db_session)
        db_session.commit()

        snapshot = snapshot_site_structure(site.id, db_session)
        # Re-validate the snapshot and confirm the captured kinds match what we applied.
        validated = validate_template_structure(snapshot)
        captured_kinds = {
            d["kind"]
            for s in validated["sections"]
            for d in s["documents"]
        }
        assert SiteDocumentsEnum.site_lease.name in captured_kinds
        assert SiteDocumentsEnum.ppa_and_amendments.name in captured_kinds

        preview = next(s for s in validated["sections"] if s["key"] == DocumentSections.preview.name)
        site_lease_node = next(d for d in preview["documents"] if d["kind"] == SiteDocumentsEnum.site_lease.name)
        assert site_lease_node["description"] == "Executed site lease."


class TestCrudScoping:
    def test_get_for_company_rejects_other_company(self, db_session, company):
        other = CompanyCRUD(db_session).create_item(
            {"name": "Other Co (templates)", "company_type": CompanyTypes.operation_maintenance_contractor}
        )
        crud = DataRoomTemplateCRUD(db_session)
        template = crud.create_item(
            {
                "company_id": company.id,
                "name": "Scoped Template",
                "structure": _sample_structure(),
            }
        )
        db_session.commit()
        try:
            assert crud.get_for_company(template.id, company.id) is not None
            # Wrong company -> scope guard returns None.
            assert crud.get_for_company(template.id, other.id) is None
        finally:
            crud.delete_by_id(template.id)
            CompanyCRUD(db_session).delete_by_id(other.id)
            db_session.commit()


class TestRouterEndpoints:
    """Exercise the router functions directly with authz patched out."""

    @pytest.fixture()
    def patched_authz(self, monkeypatch):
        monkeypatch.setattr(router_mod, "require_module_permission", Mock(return_value=None))

    @pytest.fixture()
    def current_user(self, system_user_id):
        user = Mock()
        user.id = system_user_id
        return user

    def test_create_list_export_duplicate_lifecycle(self, db_session, site, current_user, patched_authz):
        from app.schema.data_room_templates import (
            CreateTemplateSchema,
            DuplicateTemplateSchema,
            UpdateTemplateSchema,
        )

        created = asyncio.run(
            router_mod.create_template(
                payload=CreateTemplateSchema(name="Router Template", structure=_sample_structure()),
                current_user=current_user,
                site=site,
                db_session=db_session,
            )
        )
        db_session.commit()
        template_id = created["id"]
        assert created["code"] == 201

        try:
            listed = asyncio.run(
                router_mod.list_templates(current_user=current_user, site=site, db_session=db_session)
            )
            assert any(item["id"] == template_id for item in listed["items"])

            detail = asyncio.run(
                router_mod.get_template(
                    template_id=template_id, current_user=current_user, site=site, db_session=db_session
                )
            )
            assert detail["section_count"] == 2

            export = asyncio.run(
                router_mod.export_template(
                    template_id=template_id, current_user=current_user, site=site, db_session=db_session
                )
            )
            assert export["format"] == drt.EXPORT_FORMAT

            asyncio.run(
                router_mod.update_template(
                    template_id=template_id,
                    payload=UpdateTemplateSchema(name="Renamed Template"),
                    current_user=current_user,
                    site=site,
                    db_session=db_session,
                )
            )
            db_session.commit()
            assert DataRoomTemplateCRUD(db_session).get_by_id(template_id).name == "Renamed Template"

            dup = asyncio.run(
                router_mod.duplicate_template(
                    template_id=template_id,
                    payload=DuplicateTemplateSchema(),
                    current_user=current_user,
                    site=site,
                    db_session=db_session,
                )
            )
            db_session.commit()
            dup_id = dup["id"]
            assert DataRoomTemplateCRUD(db_session).get_by_id(dup_id).name == "Renamed Template (Copy)"
            DataRoomTemplateCRUD(db_session).delete_by_id(dup_id)
            db_session.commit()
        finally:
            DataRoomTemplateCRUD(db_session).delete_by_id(template_id)
            db_session.commit()

    def test_archive_hides_from_default_list(self, db_session, site, current_user, patched_authz):
        from app.schema.data_room_templates import CreateTemplateSchema

        created = asyncio.run(
            router_mod.create_template(
                payload=CreateTemplateSchema(name="Archivable", structure=_sample_structure()),
                current_user=current_user,
                site=site,
                db_session=db_session,
            )
        )
        db_session.commit()
        template_id = created["id"]
        try:
            asyncio.run(
                router_mod.archive_template(
                    template_id=template_id, current_user=current_user, site=site, db_session=db_session
                )
            )
            db_session.commit()

            default_list = asyncio.run(
                router_mod.list_templates(current_user=current_user, site=site, db_session=db_session)
            )
            assert all(item["id"] != template_id for item in default_list["items"])

            with_archived = asyncio.run(
                router_mod.list_templates(
                    current_user=current_user, site=site, include_archived=True, db_session=db_session
                )
            )
            assert any(item["id"] == template_id for item in with_archived["items"])

            asyncio.run(
                router_mod.restore_template(
                    template_id=template_id, current_user=current_user, site=site, db_session=db_session
                )
            )
            db_session.commit()
            restored_list = asyncio.run(
                router_mod.list_templates(current_user=current_user, site=site, db_session=db_session)
            )
            assert any(item["id"] == template_id for item in restored_list["items"])
        finally:
            DataRoomTemplateCRUD(db_session).delete_by_id(template_id)
            db_session.commit()

    def test_import_creates_template(self, db_session, site, current_user, patched_authz):
        from app.schema.data_room_templates import ImportTemplateSchema

        envelope = {
            "format": drt.EXPORT_FORMAT,
            "export_version": drt.EXPORT_VERSION,
            "name": "Imported Router Template",
            "description": "from-import",
            "structure": _sample_structure(),
        }
        created = asyncio.run(
            router_mod.import_template(
                payload=ImportTemplateSchema(payload=envelope),
                current_user=current_user,
                site=site,
                db_session=db_session,
            )
        )
        db_session.commit()
        template_id = created["id"]
        try:
            row = DataRoomTemplateCRUD(db_session).get_by_id(template_id)
            assert row.name == "Imported Router Template"
            assert row.description == "from-import"
        finally:
            DataRoomTemplateCRUD(db_session).delete_by_id(template_id)
            db_session.commit()

    def test_import_csv_creates_template(self, db_session, site, current_user, patched_authz):
        from app.schema.data_room_templates import ImportTemplateSchema

        csv_text = (
            "section_key,subsection_key,kind,description,guidance,required\n"
            f"{DocumentSections.preview.name},,{SiteDocumentsEnum.site_lease.name},Executed lease,,false\n"
        )
        created = asyncio.run(
            router_mod.import_template(
                payload=ImportTemplateSchema(csv=csv_text, name="CSV Imported Template"),
                current_user=current_user,
                site=site,
                db_session=db_session,
            )
        )
        db_session.commit()
        template_id = created["id"]
        try:
            row = DataRoomTemplateCRUD(db_session).get_by_id(template_id)
            assert row.name == "CSV Imported Template"
            kinds = {d["kind"] for s in row.structure["sections"] for d in s["documents"]}
            assert SiteDocumentsEnum.site_lease.name in kinds
        finally:
            DataRoomTemplateCRUD(db_session).delete_by_id(template_id)
            db_session.commit()

    def test_cross_company_template_is_not_found(self, db_session, site, current_user, patched_authz):
        from fastapi import HTTPException

        other = CompanyCRUD(db_session).create_item(
            {"name": "Other Co (router)", "company_type": CompanyTypes.operation_maintenance_contractor}
        )
        foreign = DataRoomTemplateCRUD(db_session).create_item(
            {"company_id": other.id, "name": "Foreign", "structure": _sample_structure()}
        )
        db_session.commit()
        try:
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    router_mod.get_template(
                        template_id=foreign.id, current_user=current_user, site=site, db_session=db_session
                    )
                )
            assert exc_info.value.status_code == 404
        finally:
            DataRoomTemplateCRUD(db_session).delete_by_id(foreign.id)
            CompanyCRUD(db_session).delete_by_id(other.id)
            db_session.commit()


class TestSiteCreationTemplateAuthz:
    """Applying a template during site creation must ALSO require Diligence:edit.

    The create endpoint already requires assets_management:edit; when a
    template_id is supplied, applying it is a Diligence action and must be gated
    by Diligence:edit too (Task #91 - all template actions use Diligence perms).
    """

    def _build_mock_user(self, user_id=1, is_system_user=False):
        mock_user = Mock()
        mock_user.id = user_id
        mock_user.is_system_user = is_system_user
        return mock_user

    def _build_site_payload(self, company_id=100, template_id=None):
        from app.schema.site import CreateSiteSchema

        return CreateSiteSchema(
            company_id=company_id,
            name="Templated Site",
            address="123 Main St",
            city="Springfield",
            state="NY",
            zip_code="12345",
            system_size_ac=0,
            system_size_dc=0,
            lon_lat_url="",
            template_id=template_id,
        )

    def test_template_apply_denied_without_diligence_edit(self):
        """template_id supplied but caller lacks Diligence:edit -> 403, no site created."""
        from unittest.mock import patch
        from fastapi import HTTPException

        mock_user = self._build_mock_user()
        site_payload = self._build_site_payload(company_id=42, template_id=7)

        def perm_side_effect(*, module_key, **kwargs):
            if module_key == "Diligence":
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: missing_module_permission:Diligence.edit",
                )
            return None

        with (
            patch("app.routers.assets_management.sites.require_module_permission", side_effect=perm_side_effect),
            patch("app.routers.assets_management.sites.SiteCRUD") as mock_site_crud,
            patch("app.routers.assets_management.sites.DataRoomTemplateCRUD") as mock_template_crud,
        ):
            from app.routers.assets_management.sites import create

            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(create(site=site_payload, current_user=mock_user, db_session=Mock()))

            assert exc_info.value.status_code == 403
            assert "Diligence" in str(exc_info.value.detail)
            # Fail-closed: neither the template lookup nor the site row should be created.
            mock_template_crud.return_value.get_for_company.assert_not_called()
            mock_site_crud.return_value.create_item.assert_not_called()

    def test_diligence_check_skipped_when_no_template(self):
        """Without template_id, only assets_management:edit is checked (no Diligence call)."""
        from unittest.mock import patch

        mock_user = self._build_mock_user()
        mock_db = Mock()
        site_payload = self._build_site_payload(company_id=42, template_id=None)

        mock_site_obj = Mock()
        mock_site_obj.id = 99
        mock_site_obj.company_id = 42
        mock_site_obj.documents_board = Mock()
        mock_site_obj.documents_board.related_entity = Mock()
        mock_site_obj.documents_board.related_entity.extra_entity_type = "document"
        mock_site_obj.documents = []

        with (
            patch("app.routers.assets_management.sites.require_module_permission") as mock_perm,
            patch("app.routers.assets_management.sites.SiteCRUD") as mock_site_crud,
            patch("app.routers.assets_management.sites.create_default_site_document_sections"),
            patch("app.routers.assets_management.sites.DocumentCRUD"),
            patch("app.routers.assets_management.sites.generate_default_site_documents", return_value=[]),
            patch("app.routers.assets_management.sites.create_default_board"),
            patch("app.routers.assets_management.sites.create_default_document_tasks"),
            patch("app.routers.assets_management.sites.UserProjectCRUD"),
        ):
            mock_site_crud.return_value.create_item.return_value = mock_site_obj

            from app.routers.assets_management.sites import create

            asyncio.run(create(site=site_payload, current_user=mock_user, db_session=mock_db))

            module_keys = {c.kwargs["module_key"] for c in mock_perm.call_args_list}
            assert module_keys == {"Asset Management"}

    def test_diligence_edit_checked_when_template_present(self):
        """With template_id and permission granted, Diligence:edit is checked and template applied."""
        from unittest.mock import patch

        mock_user = self._build_mock_user()
        mock_db = Mock()
        site_payload = self._build_site_payload(company_id=42, template_id=7)

        mock_site_obj = Mock()
        mock_site_obj.id = 99
        mock_site_obj.company_id = 42
        mock_site_obj.documents_board = Mock()
        mock_site_obj.documents_board.related_entity = Mock()
        mock_site_obj.documents_board.related_entity.extra_entity_type = "document"
        mock_site_obj.documents = []

        mock_template = Mock()
        mock_template.structure = _sample_structure()

        with (
            patch("app.routers.assets_management.sites.require_module_permission") as mock_perm,
            patch("app.routers.assets_management.sites.SiteCRUD") as mock_site_crud,
            patch("app.routers.assets_management.sites.DataRoomTemplateCRUD") as mock_template_crud,
            patch("app.routers.assets_management.sites.apply_template_to_site") as mock_apply,
            patch("app.routers.assets_management.sites.create_default_board"),
            patch("app.routers.assets_management.sites.create_default_document_tasks"),
            patch("app.routers.assets_management.sites.UserProjectCRUD"),
        ):
            mock_site_crud.return_value.create_item.return_value = mock_site_obj
            mock_template_crud.return_value.get_for_company.return_value = mock_template

            from app.routers.assets_management.sites import create

            asyncio.run(create(site=site_payload, current_user=mock_user, db_session=mock_db))

            module_keys = {c.kwargs["module_key"] for c in mock_perm.call_args_list}
            assert module_keys == {"Asset Management", "Diligence"}
            diligence_call = next(c for c in mock_perm.call_args_list if c.kwargs["module_key"] == "Diligence")
            assert diligence_call.kwargs["action"] == "edit"
            assert diligence_call.kwargs["company_id"] == 42
            mock_apply.assert_called_once_with(mock_site_obj.id, mock_template.structure, mock_db)

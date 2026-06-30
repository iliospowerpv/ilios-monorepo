"""Tests for Guided Upload, Duplicate Prevention & the Guidance Dashboard (Task #92).

Covers the pure name-matching helper, the read-only duplicate-check router endpoint,
and the read-only per-stage guidance dashboard endpoint. Everything here is advisory
and read-only — no Document/File rows are mutated and the canonical ``Site`` entity is
never touched.
"""
import asyncio
from unittest.mock import Mock

import pytest

from app.crud.file import FileCRUD
from app.helpers.due_diligence.document_matching import (
    IdentityCandidate,
    find_duplicate_candidates,
    normalize_name,
)
from app.models.project_facts import AssumptionPromotion
from app.routers.due_diligence import documents as router_mod
from app.static.default_site_documents_enum import SiteDocumentsEnum
from tests.utils import get_document_by_name


def _candidate(document_id, names, files_count=1, kind=None, archived=False):
    return IdentityCandidate(
        document_id=document_id,
        display_name=names[0],
        names=names,
        kind=kind,
        section_id=1,
        section_name="Preview",
        files_count=files_count,
        is_archived=archived,
    )


class TestNormalizeName:
    def test_strips_punctuation_and_case(self):
        assert normalize_name("  PVsyst - Final (v2)!! ") == "pvsyst final v2"

    def test_none_is_empty(self):
        assert normalize_name(None) == ""


class TestFindDuplicateCandidates:
    def test_exact_match(self):
        cands = [_candidate(1, ["PVsyst Final"])]
        matches = find_duplicate_candidates("pvsyst final", cands)
        assert len(matches) == 1
        assert matches[0].match_type == "exact"
        assert matches[0].score == 1.0

    def test_version_word_collapses_to_same_identity(self):
        cands = [_candidate(1, ["PVsyst Final"])]
        matches = find_duplicate_candidates("PVsyst", cands)
        assert matches[0].match_type == "exact"

    def test_near_match_on_revision_variants(self):
        cands = [_candidate(1, ["PVsyst Revised"])]
        matches = find_duplicate_candidates("PVsyst Post Permit", cands)
        assert matches
        assert matches[0].document_id == 1

    def test_alias_triggers_match(self):
        cands = [_candidate(1, ["Site Lease", "Ground Lease"], kind="site_lease")]
        matches = find_duplicate_candidates("ground lease", cands)
        assert matches and matches[0].match_type == "exact"

    def test_unrelated_name_no_match(self):
        cands = [_candidate(1, ["PVsyst Final"])]
        assert find_duplicate_candidates("Insurance Certificate", cands) == []

    def test_empty_proposed_name_no_match(self):
        cands = [_candidate(1, ["PVsyst Final"])]
        assert find_duplicate_candidates("   ", cands) == []

    def test_exact_outranks_near_and_files_break_ties(self):
        cands = [
            _candidate(1, ["PVsyst Summary"], files_count=0),  # near
            _candidate(2, ["PVsyst"], files_count=3),  # exact
        ]
        matches = find_duplicate_candidates("PVsyst", cands)
        assert matches[0].document_id == 2
        assert matches[0].match_type == "exact"

    def test_results_capped(self):
        cands = [_candidate(i, [f"PVsyst Report {i}"]) for i in range(20)]
        assert len(find_duplicate_candidates("PVsyst", cands, limit=5)) == 5


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

    def test_duplicate_check_finds_existing_identity(
        self, db_session, site, documents, current_user, patched_authz
    ):
        result = asyncio.run(
            router_mod.check_duplicate_document(
                name="Site Lease",
                site=site,
                current_user=current_user,
                db_session=db_session,
            )
        )
        assert result["proposed_name"] == "Site Lease"
        assert result["has_match"] is True
        kinds = {c["kind"] for c in result["candidates"]}
        assert SiteDocumentsEnum.site_lease.name in kinds

    def test_duplicate_check_no_match_for_novel_name(
        self, db_session, site, documents, current_user, patched_authz
    ):
        result = asyncio.run(
            router_mod.check_duplicate_document(
                name="Totally Unrelated Brand New Doc",
                site=site,
                current_user=current_user,
                db_session=db_session,
            )
        )
        assert result["has_match"] is False
        assert result["candidates"] == []

    def test_guidance_reports_present_when_file_uploaded(
        self, db_session, site, documents, non_system_user_id, current_user, patched_authz
    ):
        exec_doc = get_document_by_name(site.documents, SiteDocumentsEnum.executive_summary)
        file_crud = FileCRUD(db_session)
        uploaded = file_crud.create_item(
            {
                "filepath": "test/path/exec.pdf",
                "filename": "exec.pdf",
                "user_id": non_system_user_id,
                "document_id": exec_doc.id,
                "version_number": 1,
                "is_actual": True,
            }
        )
        db_session.commit()
        try:
            result = asyncio.run(
                router_mod.get_data_room_guidance(
                    site=site, current_user=current_user, db_session=db_session
                )
            )
            stages = {item["section_key"]: item for item in result["items"]}
            exec_stage = stages["executive_summary"]
            assert exec_stage["expected"] >= 1
            assert exec_stage["present"] >= 1
            assert exec_stage["version_count"] >= 1
            # Uploaded but never promoted -> not_started, not "complete".
            assert exec_stage["promotion_status"] == "not_started"
            assert exec_stage["needs_update"] == 0
        finally:
            file_crud.delete_by_id(uploaded.id)
            db_session.commit()

    def test_guidance_marks_needs_update_after_new_version(
        self, db_session, site, documents, non_system_user_id, system_user_id, current_user, patched_authz
    ):
        exec_doc = get_document_by_name(site.documents, SiteDocumentsEnum.executive_summary)
        file_crud = FileCRUD(db_session)
        v1 = file_crud.create_item(
            {
                "filepath": "test/path/exec_v1.pdf",
                "filename": "exec_v1.pdf",
                "user_id": non_system_user_id,
                "document_id": exec_doc.id,
                "version_number": 1,
                "is_actual": False,
            }
        )
        v2 = file_crud.create_item(
            {
                "filepath": "test/path/exec_v2.pdf",
                "filename": "exec_v2.pdf",
                "user_id": non_system_user_id,
                "document_id": exec_doc.id,
                "version_number": 2,
                "is_actual": True,
            }
        )
        db_session.commit()
        # Promotion was recorded against v1; v2 arrived afterwards -> needs update.
        promotion = AssumptionPromotion(
            site_id=site.id,
            document_id=exec_doc.id,
            file_id=v1.id,
            promoted_by_id=system_user_id,
        )
        db_session.add(promotion)
        db_session.commit()
        try:
            db_session.expire_all()
            result = asyncio.run(
                router_mod.get_data_room_guidance(
                    site=site, current_user=current_user, db_session=db_session
                )
            )
            stages = {item["section_key"]: item for item in result["items"]}
            exec_stage = stages["executive_summary"]
            assert exec_stage["needs_update"] == 1
            assert exec_stage["promotion_status"] == "in_progress"
        finally:
            db_session.delete(promotion)
            db_session.commit()
            file_crud.delete_by_id(v1.id)
            file_crud.delete_by_id(v2.id)
            db_session.commit()

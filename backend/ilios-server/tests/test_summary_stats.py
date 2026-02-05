"""Tests for project-level due diligence summary stats endpoint"""

import pytest

from app.models.project_facts import ProjectFact, FactStatus, CanonicalField
from app.models.file import FileParsingStatuses
from app.models.document import Document
from app.routers.due_diligence.summary_stats import is_meaningful_value, map_parsing_status_to_coterminus_status


class TestIsMeaningfulValue:
    """Tests for the is_meaningful_value helper function"""

    def test_null_value_is_not_meaningful(self):
        assert is_meaningful_value(None) is False

    def test_empty_string_is_not_meaningful(self):
        assert is_meaningful_value("") is False
        assert is_meaningful_value("   ") is False

    def test_na_value_is_not_meaningful(self):
        assert is_meaningful_value("N/A") is False
        assert is_meaningful_value("n/a") is False
        assert is_meaningful_value("N/a") is False

    def test_dict_with_null_v_is_not_meaningful(self):
        assert is_meaningful_value({"v": None}) is False

    def test_dict_with_empty_v_is_not_meaningful(self):
        assert is_meaningful_value({"v": ""}) is False
        assert is_meaningful_value({"v": "   "}) is False

    def test_dict_with_na_v_is_not_meaningful(self):
        assert is_meaningful_value({"v": "N/A"}) is False
        assert is_meaningful_value({"v": "n/a"}) is False

    def test_dict_with_actual_value_is_meaningful(self):
        assert is_meaningful_value({"v": "Some value"}) is True
        assert is_meaningful_value({"v": "123"}) is True
        assert is_meaningful_value({"v": "2025-01-01"}) is True

    def test_string_value_is_meaningful(self):
        assert is_meaningful_value("Some value") is True
        assert is_meaningful_value("123") is True

    def test_numeric_value_is_meaningful(self):
        assert is_meaningful_value(123) is True
        assert is_meaningful_value(0) is True
        assert is_meaningful_value(45.67) is True


class TestMapParsingStatusToCoterminusStatus:
    """Tests for the map_parsing_status_to_coterminus_status helper function"""

    def test_processing_status_returns_running(self):
        assert map_parsing_status_to_coterminus_status(FileParsingStatuses.processing) == "running"

    def test_processing_status_with_stuck_returns_stuck(self):
        assert map_parsing_status_to_coterminus_status(FileParsingStatuses.processing, is_stuck=True) == "stuck"

    def test_completed_status_returns_completed(self):
        assert map_parsing_status_to_coterminus_status(FileParsingStatuses.completed) == "completed"

    def test_processing_failed_returns_failed(self):
        assert map_parsing_status_to_coterminus_status(FileParsingStatuses.processing_failed) == "failed"

    def test_processing_start_failed_returns_failed(self):
        assert map_parsing_status_to_coterminus_status(FileParsingStatuses.processing_start_failed) == "failed"

    def test_processing_timeout_returns_stuck(self):
        assert map_parsing_status_to_coterminus_status(FileParsingStatuses.processing_timeout) == "stuck"

    def test_not_started_returns_not_run(self):
        assert map_parsing_status_to_coterminus_status(FileParsingStatuses.not_started) == "not_run"


class TestSummaryStatsEndpoint:
    """Integration tests for the summary-stats endpoint"""

    def test_endpoint_requires_authentication(self, client):
        """Test that the endpoint returns 401 without authentication"""
        response = client.get("/api/due-diligence/sites/1/summary-stats")
        assert response.status_code == 401

    def test_endpoint_returns_correct_structure(self, client, site_id, system_user_auth_header):
        """Test that the endpoint returns the expected response structure"""
        response = client.get(
            f"/api/due-diligence/sites/{site_id}/summary-stats",
            headers=system_user_auth_header
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "documents_total" in data
        assert "documents_with_promoted_terms" in data
        assert "promoted_terms_total" in data
        assert "coterminus" in data
        assert isinstance(data["coterminus"], dict)
        assert "status" in data["coterminus"]
        assert "mismatches" in data["coterminus"]
        assert "last_run_at" in data["coterminus"]

    def test_documents_total_matches_site_documents_count(
        self, client, site, db_session, system_user_auth_header
    ):
        """Test that documents_total equals the count of non-archived documents for this site"""
        from sqlalchemy import func
        
        expected_count = db_session.query(func.count(Document.id)).filter(
            Document.site_id == site.id,
            Document.is_archived == False
        ).scalar() or 0
        
        response = client.get(
            f"/api/due-diligence/sites/{site.id}/summary-stats",
            headers=system_user_auth_header
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["documents_total"] == expected_count

    def test_site_with_no_promoted_facts_returns_zeros(self, client, site_id, system_user_auth_header):
        """Test that a site without promoted facts returns zero counts"""
        response = client.get(
            f"/api/due-diligence/sites/{site_id}/summary-stats",
            headers=system_user_auth_header
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["documents_with_promoted_terms"] == 0
        assert data["promoted_terms_total"] == 0
        assert data["coterminus"]["status"] == "not_run"

    def test_promoted_facts_are_counted_correctly(
        self, client, site, db_session, system_user_auth_header, document, file
    ):
        """Test that promoted facts with meaningful values are counted correctly"""
        canonical_field = db_session.query(CanonicalField).first()
        if not canonical_field:
            canonical_field = CanonicalField(
                name="test_field",
                display_name="Test Field",
                field_type="text",
                is_active=True
            )
            db_session.add(canonical_field)
            db_session.flush()
        
        fact1 = ProjectFact(
            site_id=site.id,
            canonical_field_id=canonical_field.id,
            value={"v": "Meaningful value 1"},
            status=FactStatus.active.value,
            source_file_id=file.id
        )
        fact2 = ProjectFact(
            site_id=site.id,
            canonical_field_id=canonical_field.id,
            value={"v": "Meaningful value 2"},
            status=FactStatus.active.value,
            source_file_id=file.id
        )
        fact3 = ProjectFact(
            site_id=site.id,
            canonical_field_id=canonical_field.id,
            value={"v": "N/A"},
            status=FactStatus.active.value,
            source_file_id=file.id
        )
        db_session.add_all([fact1, fact2, fact3])
        db_session.commit()
        
        try:
            response = client.get(
                f"/api/due-diligence/sites/{site.id}/summary-stats",
                headers=system_user_auth_header
            )
            assert response.status_code == 200
            data = response.json()
            
            assert data["promoted_terms_total"] == 2
            assert data["documents_with_promoted_terms"] == 1
        finally:
            db_session.query(ProjectFact).filter(
                ProjectFact.id.in_([fact1.id, fact2.id, fact3.id])
            ).delete(synchronize_session=False)
            db_session.commit()

    def test_candidate_facts_are_not_counted(
        self, client, site, db_session, system_user_auth_header, document, file
    ):
        """Test that candidate (not promoted) facts are not counted"""
        canonical_field = db_session.query(CanonicalField).first()
        if not canonical_field:
            canonical_field = CanonicalField(
                name="test_field_candidate",
                display_name="Test Field Candidate",
                field_type="text",
                is_active=True
            )
            db_session.add(canonical_field)
            db_session.flush()
        
        candidate_fact = ProjectFact(
            site_id=site.id,
            canonical_field_id=canonical_field.id,
            value={"v": "Candidate value"},
            status=FactStatus.candidate.value,
            source_file_id=file.id
        )
        db_session.add(candidate_fact)
        db_session.commit()
        
        try:
            response = client.get(
                f"/api/due-diligence/sites/{site.id}/summary-stats",
                headers=system_user_auth_header
            )
            assert response.status_code == 200
            data = response.json()
            
            assert data["promoted_terms_total"] == 0
            assert data["documents_with_promoted_terms"] == 0
        finally:
            db_session.delete(candidate_fact)
            db_session.commit()

    def test_nonexistent_site_returns_404(self, client, system_user_auth_header):
        """Test that a nonexistent site returns 404"""
        response = client.get(
            "/api/due-diligence/sites/99999/summary-stats",
            headers=system_user_auth_header
        )
        assert response.status_code == 404

    def test_documents_with_promoted_terms_counts_distinct_documents(
        self, client, site, db_session, system_user_auth_header, document, file
    ):
        """Test that documents_with_promoted_terms counts distinct document_id"""
        canonical_field = db_session.query(CanonicalField).first()
        if not canonical_field:
            canonical_field = CanonicalField(
                name="test_field_distinct",
                display_name="Test Field Distinct",
                field_type="text",
                is_active=True
            )
            db_session.add(canonical_field)
            db_session.flush()
        
        fact1 = ProjectFact(
            site_id=site.id,
            canonical_field_id=canonical_field.id,
            value={"v": "Value 1"},
            status=FactStatus.active.value,
            source_file_id=file.id
        )
        fact2 = ProjectFact(
            site_id=site.id,
            canonical_field_id=canonical_field.id,
            value={"v": "Value 2"},
            status=FactStatus.active.value,
            source_file_id=file.id
        )
        db_session.add_all([fact1, fact2])
        db_session.commit()
        
        try:
            response = client.get(
                f"/api/due-diligence/sites/{site.id}/summary-stats",
                headers=system_user_auth_header
            )
            assert response.status_code == 200
            data = response.json()
            
            assert data["promoted_terms_total"] == 2
            assert data["documents_with_promoted_terms"] == 1
        finally:
            db_session.query(ProjectFact).filter(
                ProjectFact.id.in_([fact1.id, fact2.id])
            ).delete(synchronize_session=False)
            db_session.commit()

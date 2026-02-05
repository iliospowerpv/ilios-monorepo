"""Finance Phase F4: Health Summary Tests.

Tests verify:
1. sync_status computation for each state:
   - not_configured, never_synced, running, error, healthy
2. Permission enforcement on GET /api/finance/summary
3. Response shape correctness
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from app.crud.company import CompanyCRUD
from app.crud.finance_account import FinanceAccountCRUD
from app.crud.finance_integration import FinanceIntegrationCRUD
from app.crud.finance_sync_run import FinanceSyncRunCRUD
from app.crud.finance_transaction import FinanceTransactionCRUD
from app.crud.user import UserCRUD
from app.crud.user_company_access import UserCompanyAccessCRUD
from app.helpers.authentication import get_current_user
from app.models.finance_sync_run import FinanceSyncRun, FinanceSyncRunStatus
from app.schema.user import CurrentUserSchema
from app.services.finance.health_service import FinanceHealthService
from tests.conftest import test_app, get_test_session


def _mock_user(user, company_ids, is_system_user=False):
    mock = Mock(spec=CurrentUserSchema)
    mock.id = user.id
    mock.is_system_user = is_system_user
    mock.role = Mock()
    mock.role.permissions = {}
    mock.get_limited_companies_ids.return_value = company_ids
    mock.get_limited_sites_ids.return_value = []
    return mock


class F4FixtureFactory:

    @staticmethod
    def create_company(db, name="F4 Test Company"):
        return CompanyCRUD(db).create_item({
            "name": name,
            "company_type": "Portfolio Management",
        })

    @staticmethod
    def create_user_with_access(db, email, company_id, role="contributor"):
        user = UserCRUD(db).create_item({
            "first_name": "Test",
            "last_name": email.split("@")[0],
            "email": email,
            "is_registered": True,
            "phone": "1234567890",
        })
        access = UserCompanyAccessCRUD(db).create_item({
            "user_id": user.id,
            "company_id": company_id,
            "role": role,
            "status": "active",
        })
        return {"user": user, "access": access}

    @staticmethod
    def create_integration(db, company_id, provider_key="gravity", use_stub=True):
        crud = FinanceIntegrationCRUD(db)
        return crud.create_integration(
            company_id=company_id,
            provider_key=provider_key,
            credentials={"api_key": "test-key", "api_secret": "test-secret"},
            config={"use_stub_data": use_stub},
        )

    @staticmethod
    def create_sync_run(db, company_id, status_val, provider_key="gravity",
                        last_error=None, ended_at=None, started_at=None):
        import uuid
        run = FinanceSyncRun(
            company_id=company_id,
            provider_key=provider_key,
            status=status_val,
            correlation_id=str(uuid.uuid4()),
            started_at=started_at or datetime.utcnow(),
            ended_at=ended_at,
            last_error=last_error,
            last_successful_sync_at=ended_at if status_val == FinanceSyncRunStatus.succeeded else None,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    @staticmethod
    def cleanup(db, company, users, integration=None):
        from app.models.finance_transaction import FinanceTransaction
        from app.models.finance_account import FinanceAccount
        from app.models.finance_sync_run import FinanceSyncRun as SyncRunModel

        if integration:
            FinanceIntegrationCRUD(db).delete_integration(integration.id)

        db.query(FinanceTransaction).filter_by(company_id=company.id).delete()
        db.query(FinanceAccount).filter_by(company_id=company.id).delete()
        db.query(SyncRunModel).filter_by(company_id=company.id).delete()
        db.commit()

        for u in users:
            if u.get("access"):
                UserCompanyAccessCRUD(db).delete_by_id(u["access"].id)
            if u.get("user"):
                UserCRUD(db).delete_by_id(u["user"].id)

        CompanyCRUD(db).delete_by_id(company.id)


class TestFinanceHealthServiceUnit:
    """Test FinanceHealthService.compute_summary for each sync_status state."""

    @pytest.fixture(scope="function")
    def db(self):
        return next(get_test_session())

    def test_not_configured(self, db):
        """No integration exists -> not_configured."""
        factory = F4FixtureFactory
        company = factory.create_company(db, "NotConfigured Co")
        admin = factory.create_user_with_access(db, "nc_admin@test.com", company.id, "company_admin")

        try:
            svc = FinanceHealthService(db)
            result = svc.compute_summary(company.id)

            assert result.sync_status == "not_configured"
            assert result.accounts_count == 0
            assert result.transactions_count_30d == 0
            assert "no_integration_configured" in result.needs_attention_reasons
        finally:
            factory.cleanup(db, company, [admin])

    def test_never_synced(self, db):
        """Integration exists but no sync runs -> never_synced."""
        factory = F4FixtureFactory
        company = factory.create_company(db, "NeverSynced Co")
        admin = factory.create_user_with_access(db, "ns_admin@test.com", company.id, "company_admin")
        integration = factory.create_integration(db, company.id)

        try:
            svc = FinanceHealthService(db)
            result = svc.compute_summary(company.id)

            assert result.sync_status == "never_synced"
            assert "never_synced" in result.needs_attention_reasons
        finally:
            factory.cleanup(db, company, [admin], integration)

    def test_running(self, db):
        """Latest sync run is running -> running."""
        factory = F4FixtureFactory
        company = factory.create_company(db, "Running Co")
        admin = factory.create_user_with_access(db, "run_admin@test.com", company.id, "company_admin")
        integration = factory.create_integration(db, company.id)
        factory.create_sync_run(db, company.id, FinanceSyncRunStatus.running)

        try:
            svc = FinanceHealthService(db)
            result = svc.compute_summary(company.id)

            assert result.sync_status == "running"
        finally:
            factory.cleanup(db, company, [admin], integration)

    def test_error_failed_sync(self, db):
        """Latest sync run failed -> error."""
        factory = F4FixtureFactory
        company = factory.create_company(db, "ErrorSync Co")
        admin = factory.create_user_with_access(db, "err_admin@test.com", company.id, "company_admin")
        integration = factory.create_integration(db, company.id)
        factory.create_sync_run(
            db, company.id, FinanceSyncRunStatus.failed,
            last_error="Connection timeout",
            ended_at=datetime.utcnow(),
        )

        try:
            svc = FinanceHealthService(db)
            result = svc.compute_summary(company.id)

            assert result.sync_status == "error"
            assert result.last_sync_error == "Connection timeout"
            assert "last_sync_failed" in result.needs_attention_reasons
        finally:
            factory.cleanup(db, company, [admin], integration)

    def test_healthy_recent_sync(self, db):
        """Recent successful sync (within 24h) -> healthy."""
        factory = F4FixtureFactory
        company = factory.create_company(db, "Healthy Co")
        admin = factory.create_user_with_access(db, "healthy_admin@test.com", company.id, "company_admin")
        integration = factory.create_integration(db, company.id)

        from app.services.finance.sync_service import FinanceSyncService
        sync_svc = FinanceSyncService(db)
        sync_svc.execute_sync(company.id, "gravity", admin["user"].id)

        try:
            svc = FinanceHealthService(db)
            result = svc.compute_summary(company.id)

            assert result.sync_status == "healthy"
            assert result.last_sync_at is not None
            assert result.accounts_count > 0
            assert result.last_sync_error is None
            assert len(result.needs_attention_reasons) == 0
        finally:
            factory.cleanup(db, company, [admin], integration)

    def test_stale_sync_becomes_error(self, db):
        """Successful sync older than 24h -> error with sync_stale reason."""
        factory = F4FixtureFactory
        company = factory.create_company(db, "Stale Co")
        admin = factory.create_user_with_access(db, "stale_admin@test.com", company.id, "company_admin")
        integration = factory.create_integration(db, company.id)

        old_time = datetime.utcnow() - timedelta(hours=25)
        factory.create_sync_run(
            db, company.id, FinanceSyncRunStatus.succeeded,
            ended_at=old_time, started_at=old_time,
        )

        try:
            svc = FinanceHealthService(db)
            result = svc.compute_summary(company.id)

            assert result.sync_status == "error"
            assert "sync_stale" in result.needs_attention_reasons
        finally:
            factory.cleanup(db, company, [admin], integration)


class TestFinanceHealthEndpoint:
    """Test GET /api/finance/summary endpoint permissions and response."""

    @pytest.fixture(scope="function")
    def setup(self):
        db = next(get_test_session())
        factory = F4FixtureFactory

        company = factory.create_company(db, "Summary Endpoint Co")
        admin = factory.create_user_with_access(
            db, "summ_admin@test.com", company.id, "company_admin"
        )
        read_only = factory.create_user_with_access(
            db, "summ_ro@test.com", company.id, "read_only"
        )
        integration = factory.create_integration(db, company.id)

        yield {
            "db": db,
            "company": company,
            "admin": admin,
            "read_only": read_only,
            "integration": integration,
        }

        factory.cleanup(db, company, [admin, read_only], integration)

    def test_admin_can_read_summary(self, setup, test_app):
        """company_admin can read finance summary."""
        fixtures = setup
        company_id = fixtures["company"].id
        user_data = fixtures["admin"]

        mock = _mock_user(user_data["user"], [company_id])
        test_app.dependency_overrides[get_current_user] = lambda: mock

        try:
            r = test_app.get(f"/api/finance/summary?company_id={company_id}")
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
            data = r.json()
            assert "sync_status" in data
            assert "accounts_count" in data
            assert "transactions_count_30d" in data
            assert "needs_attention_reasons" in data
            assert isinstance(data["needs_attention_reasons"], list)
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_read_only_can_read_summary(self, setup, test_app):
        """read_only user with finance:view can read summary."""
        fixtures = setup
        company_id = fixtures["company"].id
        user_data = fixtures["read_only"]

        mock = _mock_user(user_data["user"], [company_id])
        test_app.dependency_overrides[get_current_user] = lambda: mock

        try:
            r = test_app.get(f"/api/finance/summary?company_id={company_id}")
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_summary_never_synced_state(self, setup, test_app):
        """Integration configured but no sync -> never_synced."""
        fixtures = setup
        company_id = fixtures["company"].id
        user_data = fixtures["admin"]

        mock = _mock_user(user_data["user"], [company_id])
        test_app.dependency_overrides[get_current_user] = lambda: mock

        try:
            r = test_app.get(f"/api/finance/summary?company_id={company_id}")
            assert r.status_code == 200
            data = r.json()
            assert data["sync_status"] == "never_synced"
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_summary_healthy_after_sync(self, setup, test_app):
        """After a successful sync, summary returns healthy."""
        fixtures = setup
        company_id = fixtures["company"].id
        admin = fixtures["admin"]
        db = fixtures["db"]

        from app.services.finance.sync_service import FinanceSyncService
        svc = FinanceSyncService(db)
        svc.execute_sync(company_id, "gravity", admin["user"].id)

        mock = _mock_user(admin["user"], [company_id])
        test_app.dependency_overrides[get_current_user] = lambda: mock

        try:
            r = test_app.get(f"/api/finance/summary?company_id={company_id}")
            assert r.status_code == 200
            data = r.json()
            assert data["sync_status"] == "healthy"
            assert data["accounts_count"] == 3
            assert data["last_sync_at"] is not None
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_summary_requires_company_id(self, setup, test_app):
        """Missing company_id query param -> 422."""
        fixtures = setup
        admin = fixtures["admin"]

        mock = _mock_user(admin["user"], [fixtures["company"].id])
        test_app.dependency_overrides[get_current_user] = lambda: mock

        try:
            r = test_app.get("/api/finance/summary")
            assert r.status_code == 422
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

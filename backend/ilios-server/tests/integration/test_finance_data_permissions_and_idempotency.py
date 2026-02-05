"""Finance Data Phase F3: Permission + Idempotency Tests.

Tests verify:
1. Idempotency: run sync twice -> no duplicate accounts/transactions
2. Permissions:
   - contributor/read_only cannot POST sync (requires company_admin + finance:edit)
   - Users with finance:view CAN read accounts/transactions/sync-runs
3. Response correctness: list endpoints return normalized data
"""

import pytest
from unittest.mock import Mock

from app.crud.company import CompanyCRUD
from app.crud.finance_account import FinanceAccountCRUD
from app.crud.finance_integration import FinanceIntegrationCRUD
from app.crud.finance_sync_run import FinanceSyncRunCRUD
from app.crud.finance_transaction import FinanceTransactionCRUD
from app.crud.user import UserCRUD
from app.crud.user_company_access import UserCompanyAccessCRUD
from app.helpers.authentication import get_current_user
from app.schema.user import CurrentUserSchema
from app.static.permissions import PermissionsModules
from tests.conftest import test_app, get_test_session


def _mock_user(user, company_ids, is_system_user=False):
    """Create a mock current user for auth override."""
    mock = Mock(spec=CurrentUserSchema)
    mock.id = user.id
    mock.is_system_user = is_system_user
    mock.role = Mock()
    mock.role.permissions = {}
    mock.get_limited_companies_ids.return_value = company_ids
    mock.get_limited_sites_ids.return_value = []
    return mock


class F3FixtureFactory:
    """Factory for F3 test fixtures."""

    @staticmethod
    def create_company(db, name="F3 Test Company"):
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
            credentials={"api_key": "test-key-12345", "api_secret": "test-secret-12345"},
            config={"use_stub_data": use_stub},
        )

    @staticmethod
    def cleanup(db, company, users, integration=None):
        if integration:
            FinanceIntegrationCRUD(db).delete_integration(integration.id)

        db.execute(
            FinanceTransactionCRUD(db).db_session.query(
                __import__("app.models.finance_transaction", fromlist=["FinanceTransaction"]).FinanceTransaction
            ).filter_by(company_id=company.id).delete.__func__.__code__
        ) if False else None

        from app.models.finance_transaction import FinanceTransaction
        from app.models.finance_account import FinanceAccount
        from app.models.finance_sync_run import FinanceSyncRun
        db.query(FinanceTransaction).filter_by(company_id=company.id).delete()
        db.query(FinanceAccount).filter_by(company_id=company.id).delete()
        db.query(FinanceSyncRun).filter_by(company_id=company.id).delete()
        db.commit()

        for u in users:
            if u.get("access"):
                UserCompanyAccessCRUD(db).delete_by_id(u["access"].id)
            if u.get("user"):
                UserCRUD(db).delete_by_id(u["user"].id)

        CompanyCRUD(db).delete_by_id(company.id)


class TestFinanceSyncIdempotency:
    """Test that running sync twice does not create duplicates."""

    @pytest.fixture(scope="function")
    def setup(self):
        db = next(get_test_session())
        factory = F3FixtureFactory

        company = factory.create_company(db, "Idempotency Test Co")
        admin = factory.create_user_with_access(
            db, "idempotent_admin@test.com", company.id, "company_admin"
        )
        integration = factory.create_integration(db, company.id)

        yield {
            "db": db,
            "company": company,
            "admin": admin,
            "integration": integration,
        }

        factory.cleanup(db, company, [admin], integration)

    def test_sync_twice_no_duplicates(self, setup, test_app):
        """Run sync twice; account and transaction counts must not double."""
        fixtures = setup
        company_id = fixtures["company"].id
        admin = fixtures["admin"]
        db = fixtures["db"]

        mock = _mock_user(admin["user"], [company_id])
        test_app.dependency_overrides[get_current_user] = lambda: mock

        try:
            r1 = test_app.post(f"/api/finance/integrations/{company_id}/gravity/sync")
            assert r1.status_code == 200, f"First sync failed: {r1.text}"
            data1 = r1.json()
            assert data1["status"] == "succeeded"

            acct_count_1 = FinanceAccountCRUD(db).count_by_company_provider(
                company_id, "gravity"
            )
            txn_count_1 = FinanceTransactionCRUD(db).count_by_company_provider(
                company_id, "gravity"
            )
            assert acct_count_1 > 0, "Expected accounts after first sync"
            assert txn_count_1 > 0, "Expected transactions after first sync"

            r2 = test_app.post(f"/api/finance/integrations/{company_id}/gravity/sync")
            assert r2.status_code == 200, f"Second sync failed: {r2.text}"
            data2 = r2.json()
            assert data2["status"] == "succeeded"

            acct_count_2 = FinanceAccountCRUD(db).count_by_company_provider(
                company_id, "gravity"
            )
            txn_count_2 = FinanceTransactionCRUD(db).count_by_company_provider(
                company_id, "gravity"
            )
            assert acct_count_2 == acct_count_1, (
                f"Account count doubled: {acct_count_1} -> {acct_count_2}"
            )
            assert txn_count_2 == txn_count_1, (
                f"Transaction count doubled: {txn_count_1} -> {txn_count_2}"
            )
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)


class TestFinanceDataPermissions:
    """Test permission enforcement on data endpoints."""

    @pytest.fixture(scope="function")
    def setup(self):
        db = next(get_test_session())
        factory = F3FixtureFactory

        company = factory.create_company(db, "Permissions Test Co")
        admin = factory.create_user_with_access(
            db, "data_admin@test.com", company.id, "company_admin"
        )
        contributor = factory.create_user_with_access(
            db, "data_contrib@test.com", company.id, "contributor"
        )
        read_only = factory.create_user_with_access(
            db, "data_ro@test.com", company.id, "read_only"
        )
        integration = factory.create_integration(db, company.id)

        yield {
            "db": db,
            "company": company,
            "admin": admin,
            "contributor": contributor,
            "read_only": read_only,
            "integration": integration,
        }

        factory.cleanup(db, company, [admin, contributor, read_only], integration)

    def test_contributor_cannot_trigger_sync(self, setup, test_app):
        """contributor has finance view+edit but not company_admin role -> 403 on sync."""
        fixtures = setup
        company_id = fixtures["company"].id
        user_data = fixtures["contributor"]

        mock = _mock_user(user_data["user"], [company_id])
        test_app.dependency_overrides[get_current_user] = lambda: mock

        try:
            r = test_app.post(f"/api/finance/integrations/{company_id}/gravity/sync")
            assert r.status_code == 403, f"Expected 403, got {r.status_code}"
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_read_only_cannot_trigger_sync(self, setup, test_app):
        """read_only has finance view only -> 403 on sync (needs edit)."""
        fixtures = setup
        company_id = fixtures["company"].id
        user_data = fixtures["read_only"]

        mock = _mock_user(user_data["user"], [company_id])
        test_app.dependency_overrides[get_current_user] = lambda: mock

        try:
            r = test_app.post(f"/api/finance/integrations/{company_id}/gravity/sync")
            assert r.status_code == 403, f"Expected 403, got {r.status_code}"
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_company_admin_can_read_accounts(self, setup, test_app):
        """company_admin can read accounts (finance:view implied by edit)."""
        fixtures = setup
        company_id = fixtures["company"].id
        user_data = fixtures["admin"]

        mock = _mock_user(user_data["user"], [company_id])
        test_app.dependency_overrides[get_current_user] = lambda: mock

        try:
            r = test_app.get(
                f"/api/finance/accounts?company_id={company_id}"
            )
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
            data = r.json()
            assert "accounts" in data
            assert "total" in data
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_read_only_can_read_transactions(self, setup, test_app):
        """read_only has finance:view -> can read transactions."""
        fixtures = setup
        company_id = fixtures["company"].id
        user_data = fixtures["read_only"]

        mock = _mock_user(user_data["user"], [company_id])
        test_app.dependency_overrides[get_current_user] = lambda: mock

        try:
            r = test_app.get(
                f"/api/finance/transactions?company_id={company_id}"
            )
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
            data = r.json()
            assert "transactions" in data
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_read_only_can_read_sync_runs(self, setup, test_app):
        """read_only has finance:view -> can read sync runs."""
        fixtures = setup
        company_id = fixtures["company"].id
        user_data = fixtures["read_only"]

        mock = _mock_user(user_data["user"], [company_id])
        test_app.dependency_overrides[get_current_user] = lambda: mock

        try:
            r = test_app.get(
                f"/api/finance/sync-runs?company_id={company_id}"
            )
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
            data = r.json()
            assert "sync_runs" in data
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)


class TestFinanceDataResponseCorrectness:
    """Test that list endpoints return properly normalized data after sync."""

    @pytest.fixture(scope="function")
    def synced_setup(self):
        db = next(get_test_session())
        factory = F3FixtureFactory

        company = factory.create_company(db, "Response Test Co")
        admin = factory.create_user_with_access(
            db, "resp_admin@test.com", company.id, "company_admin"
        )
        integration = factory.create_integration(db, company.id)

        from app.services.finance.sync_service import FinanceSyncService
        svc = FinanceSyncService(db)
        run = svc.execute_sync(company.id, "gravity", admin["user"].id)

        yield {
            "db": db,
            "company": company,
            "admin": admin,
            "integration": integration,
            "run": run,
        }

        factory.cleanup(db, company, [admin], integration)

    def test_accounts_response_shape(self, synced_setup, test_app):
        fixtures = synced_setup
        company_id = fixtures["company"].id
        admin = fixtures["admin"]

        mock = _mock_user(admin["user"], [company_id])
        test_app.dependency_overrides[get_current_user] = lambda: mock

        try:
            r = test_app.get(
                f"/api/finance/accounts?company_id={company_id}"
            )
            assert r.status_code == 200
            data = r.json()
            assert data["total"] == 3
            acct = data["accounts"][0]
            assert "external_id" in acct
            assert "name" in acct
            assert "provider_key" in acct
            assert acct["provider_key"] == "gravity"
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_transactions_response_shape(self, synced_setup, test_app):
        fixtures = synced_setup
        company_id = fixtures["company"].id
        admin = fixtures["admin"]

        mock = _mock_user(admin["user"], [company_id])
        test_app.dependency_overrides[get_current_user] = lambda: mock

        try:
            r = test_app.get(
                f"/api/finance/transactions?company_id={company_id}"
            )
            assert r.status_code == 200
            data = r.json()
            assert data["total"] == 5
            txn = data["transactions"][0]
            assert "external_id" in txn
            assert "amount" in txn
            assert "txn_date" in txn
            assert "account_external_id" in txn
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_sync_runs_response_shape(self, synced_setup, test_app):
        fixtures = synced_setup
        company_id = fixtures["company"].id
        admin = fixtures["admin"]

        mock = _mock_user(admin["user"], [company_id])
        test_app.dependency_overrides[get_current_user] = lambda: mock

        try:
            r = test_app.get(
                f"/api/finance/sync-runs?company_id={company_id}"
            )
            assert r.status_code == 200
            data = r.json()
            assert data["total"] >= 1
            run = data["sync_runs"][0]
            assert run["status"] == "succeeded"
            assert "correlation_id" in run
            assert run["stats_json"]["accounts_upserted"] > 0
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

import os
from unittest.mock import Mock

import pytest
from dotenv import load_dotenv
from fastapi import Depends
from fastapi.testclient import TestClient
from pydantic import PostgresDsn
from sqlalchemy import create_engine
from sqlalchemy.orm import close_all_sessions, sessionmaker

from app.db.base import Base
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.default_roles_helper import DefaultRolesHelper
from app.helpers.initial_setup_helper import AppInitHelper
from app.main import ilios_api
from app.settings import settings

# use separate database for tests, do not break the real DB
load_dotenv()
TEST_DB_NAME = os.getenv("test_db_name")
test_db_dsn = PostgresDsn.build(
    scheme="postgresql+psycopg2",
    username=settings.db_user,
    password=settings.db_password,
    host=settings.db_host,
    path=TEST_DB_NAME,
).unicode_string()

engine = create_engine(test_db_dsn, pool_size=10, max_overflow=20)

TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

test_app = ilios_api()

pytest_plugins = [
    "tests.fixtures.alerts",
    "tests.fixtures.attachments",
    "tests.fixtures.big_query",
    "tests.fixtures.boards",
    "tests.fixtures.connections",
    "tests.fixtures.configs",
    "tests.fixtures.comments",
    "tests.fixtures.companies",
    "tests.fixtures.devices",
    "tests.fixtures.device_documents",
    "tests.fixtures.documents",
    "tests.fixtures.files",
    "tests.fixtures.project_access",
    "tests.fixtures.responses",
    "tests.fixtures.roles",
    "tests.fixtures.sites",
    "tests.fixtures.tasks",
    "tests.fixtures.telemetry",
    "tests.fixtures.users",
    "tests.fixtures.notifications",
    "tests.fixtures.gcs",
    "tests.fixtures.site_visits",
    "tests.fixtures.power_bi",
]


def get_test_session() -> TestingSession:
    """Return DB session for the test DB engine"""
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


test_app.dependency_overrides[get_session] = get_test_session


@pytest.fixture()
def db_session_spy():
    """Patch the db session app's dependency with mock."""
    db_session_spy = Mock()
    test_app.dependency_overrides[get_session] = lambda: db_session_spy
    # why lambda? https://github.com/tiangolo/fastapi/issues/3331

    yield db_session_spy

    test_app.dependency_overrides[get_session] = get_test_session


@pytest.fixture(scope="session")
def db_session():
    """The main fixture for the DB session interactions. Please, use it whenever it's possible"""
    yield next(get_test_session())


@pytest.fixture(scope="session")
def client():
    """
    Sample pytest fixture.
    Docs: http://doc.pytest.org/en/latest/fixture.html
    """

    # create specific route to validate auth processing
    @test_app.get(
        "/auth-test",
    )
    async def auth_test(current_user=Depends(get_current_user)) -> dict:  # noqa: U100
        """Dummy router to check auth dependencies"""
        return {"message": "test"}

    # adjust project settings
    # turn off logger otherwise it throws error since request object client is not accessible
    # AttributeError: 'NoneType' object has no attribute 'host'
    settings.enable_requests_logger = False

    with TestClient(test_app) as client:
        # we patched db session dependency, but middlewares don't support deps so need to patch for them again:
        middleware = client.app.middleware_stack
        while middleware:
            if hasattr(middleware, "db_session"):
                middleware.db_session = next(get_test_session())
            try:
                middleware = middleware.app
            except AttributeError:
                break

        yield client


@pytest.fixture(scope="session", autouse=True)
def lifecycle_of_pytest_session(db_session):
    """Run setup and teardown before and after tests execution."""
    # setup
    Base.metadata.create_all(bind=engine)
    DefaultRolesHelper(db_session).create_default_user_roles()
    AppInitHelper(db_session).set_predefined_data()

    yield

    # teardown
    close_all_sessions()
    Base.metadata.drop_all(bind=engine)

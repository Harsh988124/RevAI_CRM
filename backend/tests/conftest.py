import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.db.base import Base
from app.db.session import get_db
import app.models  # noqa: F401
from app.main import app

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError(
        "Set TEST_DATABASE_URL to your dedicated revpilot_test_db database."
    )

parsed_url = make_url(TEST_DATABASE_URL)

if parsed_url.database != "revpilot_test_db":
    raise RuntimeError(
        "Tests may only run against a database named revpilot_test_db."
    )

test_engine = create_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)


@pytest.fixture()
def reset_test_database():
    # This drops and recreates mapped CRM tables.
    # It is safe only because the URL is restricted to revpilot_test_db.
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    yield

    Base.metadata.drop_all(bind=test_engine)



from types import SimpleNamespace

from app.api.dependencies import get_current_user


@pytest.fixture()
def client(reset_test_database):
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_current_user():
        # Existing API tests run as an authenticated manager.
        return SimpleNamespace(
            id=1,
            email="test-manager@example.com",
            full_name="Test Manager",
            role="manager",
            is_active=True,
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = (
        override_get_current_user
    )

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()

@pytest.fixture()
def anonymous_client(reset_test_database):
    # Database is available, but no authentication override is installed.
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()

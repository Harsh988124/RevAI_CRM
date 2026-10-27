
import pytest

from app.core.config import settings
from app.core.security import hash_password
from app.models import User
from tests.conftest import TestingSessionLocal


def seed_user(
    email="manager@example.com",
    role="manager",
    password="Secure-Test-Password-123!",
):
    with TestingSessionLocal() as db:
        user = User(
            email=email,
            full_name="Test User",
            hashed_password=hash_password(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id


def test_protected_api_rejects_missing_token(anonymous_client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "jwt_secret_key",
        "test-only-secret-for-auth-tests",
    )

    response = anonymous_client.get("/api/v1/companies")

    assert response.status_code == 401


def test_login_and_access_protected_endpoint(
    anonymous_client,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "jwt_secret_key",
        "test-only-secret-for-auth-tests",
    )

    seed_user()

    response = anonymous_client.post(
        "/api/v1/auth/login",
        json={
            "email": "manager@example.com",
            "password": "Secure-Test-Password-123!",
        },
    )

    assert response.status_code == 200, response.text
    token = response.json()["access_token"]

    assert response.json()["token_type"] == "bearer"

    protected = anonymous_client.get(
        "/api/v1/companies",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert protected.status_code == 200


def test_login_rejects_wrong_password(
    anonymous_client,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "jwt_secret_key",
        "test-only-secret-for-auth-tests",
    )

    seed_user()

    response = anonymous_client.post(
        "/api/v1/auth/login",
        json={
            "email": "manager@example.com",
            "password": "incorrect-password",
        },
    )

    assert response.status_code == 401


def test_sales_rep_cannot_create_policy(
    anonymous_client,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "jwt_secret_key",
        "test-only-secret-for-auth-tests",
    )

    seed_user(
        email="rep@example.com",
        role="sales_rep",
    )

    login = anonymous_client.post(
        "/api/v1/auth/login",
        json={
            "email": "rep@example.com",
            "password": "Secure-Test-Password-123!",
        },
    )

    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    response = anonymous_client.post(
        "/api/v1/policies",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "policy_key": "manager_only_test_policy",
            "name": "Manager only test policy",
            "description": "Test role-based access.",
            "from_stage": "qualification",
            "to_stage": "proposal",
            "required_fields": ["contact_id"],
            "min_amount": None,
            "min_probability": None,
            "require_open_task": False,
        },
    )

    assert response.status_code == 403

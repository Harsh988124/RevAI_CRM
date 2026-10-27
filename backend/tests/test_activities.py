
def create_company(client, name="Activity Test Company"):
    response = client.post(
        "/api/v1/companies",
        json={"name": name},
    )
    assert response.status_code == 201
    return response.json()


def test_create_activity(client):
    company = create_company(client)

    response = client.post(
        "/api/v1/activities",
        json={
            "activity_type": "call",
            "subject": "Discovery call",
            "description": "Discussed CRM requirements",
            "outcome": "Interested",
            "duration_minutes": 30,
            "company_id": company["id"],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["subject"] == "Discovery call"
    assert data["activity_type"] == "call"
    assert data["company_id"] == company["id"]


def test_list_activities(client):
    company = create_company(client)

    for activity_type, subject in [
        ("call", "Introductory call"),
        ("meeting", "Product meeting"),
    ]:
        response = client.post(
            "/api/v1/activities",
            json={
                "activity_type": activity_type,
                "subject": subject,
                "company_id": company["id"],
            },
        )
        assert response.status_code == 201

    response = client.get("/api/v1/activities?activity_type=call")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["activity_type"] == "call"


def test_get_activity(client):
    company = create_company(client)

    created = client.post(
        "/api/v1/activities",
        json={
            "activity_type": "email",
            "subject": "Follow-up email",
            "company_id": company["id"],
        },
    ).json()

    response = client.get(f"/api/v1/activities/{created['id']}")

    assert response.status_code == 200
    assert response.json()["subject"] == "Follow-up email"


def test_update_activity(client):
    company = create_company(client)

    created = client.post(
        "/api/v1/activities",
        json={
            "activity_type": "call",
            "subject": "Initial call",
            "company_id": company["id"],
        },
    ).json()

    response = client.patch(
        f"/api/v1/activities/{created['id']}",
        json={"subject": "Completed discovery call", "outcome": "Positive"},
    )

    assert response.status_code == 200
    assert response.json()["subject"] == "Completed discovery call"
    assert response.json()["outcome"] == "Positive"


def test_invalid_activity_type_returns_422(client):
    response = client.post(
        "/api/v1/activities",
        json={"activity_type": "webinar", "subject": "Test"},
    )

    assert response.status_code == 422


def test_activity_with_missing_company_returns_404(client):
    response = client.post(
        "/api/v1/activities",
        json={
            "activity_type": "call",
            "subject": "Test call",
            "company_id": 999999999,
        },
    )

    assert response.status_code == 404


def test_empty_activity_update_returns_422(client):
    company = create_company(client)
    created = client.post(
        "/api/v1/activities",
        json={
            "activity_type": "note",
            "subject": "Important note",
            "company_id": company["id"],
        },
    ).json()

    response = client.patch(
        f"/api/v1/activities/{created['id']}",
        json={},
    )

    assert response.status_code == 422


def test_delete_activity(client):
    company = create_company(client)
    created = client.post(
        "/api/v1/activities",
        json={
            "activity_type": "note",
            "subject": "Delete me",
            "company_id": company["id"],
        },
    ).json()

    activity_id = created["id"]
    response = client.delete(f"/api/v1/activities/{activity_id}")

    assert response.status_code == 204
    assert client.get(f"/api/v1/activities/{activity_id}").status_code == 404

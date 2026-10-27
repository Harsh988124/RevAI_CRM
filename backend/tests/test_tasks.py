
def create_company(client, name="Task Test Company"):
    response = client.post(
        "/api/v1/companies",
        json={"name": name},
    )
    assert response.status_code == 201
    return response.json()


def create_task(client, company_id, **overrides):
    payload = {
        "title": "Follow up with customer",
        "description": "Send the product proposal",
        "priority": "high",
        "due_at": "2026-11-01T10:00:00Z",
        "assigned_to": "sales@example.com",
        "company_id": company_id,
    }
    payload.update(overrides)
    return client.post("/api/v1/tasks", json=payload)


def test_create_task(client):
    company = create_company(client)
    response = create_task(client, company["id"])

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Follow up with customer"
    assert data["status"] == "todo"
    assert data["priority"] == "high"
    assert data["company_id"] == company["id"]
    assert data["completed_at"] is None


def test_list_tasks(client):
    company = create_company(client)
    create_task(client, company["id"])
    create_task(
        client,
        company["id"],
        title="Low priority follow-up",
        priority="low",
    )

    response = client.get("/api/v1/tasks?priority=high")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["priority"] == "high"


def test_get_task(client):
    company = create_company(client)
    created = create_task(client, company["id"]).json()

    response = client.get(f"/api/v1/tasks/{created['id']}")

    assert response.status_code == 200
    assert response.json()["title"] == "Follow up with customer"


def test_complete_task_sets_completed_at(client):
    company = create_company(client)
    created = create_task(client, company["id"]).json()

    response = client.patch(
        f"/api/v1/tasks/{created['id']}",
        json={"status": "completed"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["completed_at"] is not None


def test_reopening_task_clears_completed_at(client):
    company = create_company(client)
    created = create_task(client, company["id"]).json()

    completed = client.patch(
        f"/api/v1/tasks/{created['id']}",
        json={"status": "completed"},
    )
    assert completed.status_code == 200

    reopened = client.patch(
        f"/api/v1/tasks/{created['id']}",
        json={"status": "in_progress"},
    )

    assert reopened.status_code == 200
    assert reopened.json()["status"] == "in_progress"
    assert reopened.json()["completed_at"] is None


def test_invalid_task_priority_returns_422(client):
    company = create_company(client)

    response = create_task(
        client,
        company["id"],
        priority="critical",
    )

    assert response.status_code == 422


def test_task_with_missing_company_returns_404(client):
    response = create_task(client, 999999999)
    assert response.status_code == 404


def test_empty_task_update_returns_422(client):
    company = create_company(client)
    created = create_task(client, company["id"]).json()

    response = client.patch(
        f"/api/v1/tasks/{created['id']}",
        json={},
    )

    assert response.status_code == 422


def test_delete_task(client):
    company = create_company(client)
    created = create_task(client, company["id"]).json()

    task_id = created["id"]
    response = client.delete(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 204
    assert client.get(f"/api/v1/tasks/{task_id}").status_code == 404

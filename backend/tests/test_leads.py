
def create_company(client, name="Lead Test Company"):
    response = client.post(
        "/api/v1/companies",
        json={"name": name},
    )
    assert response.status_code == 201
    return response.json()


def create_contact(client, company_id=None):
    response = client.post(
        "/api/v1/contacts",
        json={
            "first_name": "Maya",
            "last_name": "Patel",
            "email": "maya@example.com",
            "company_id": company_id,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_lead(client, **overrides):
    payload = {
        "first_name": "Arjun",
        "last_name": "Deshmukh",
        "email": "arjun@example.com",
        "phone": "9876543210",
        "status": "new",
        "source": "website",
        "estimated_value": "15000.00",
        "company_id": None,
        "contact_id": None,
    }
    payload.update(overrides)
    return client.post("/api/v1/leads", json=payload)


def test_create_lead(client):
    response = create_lead(client)

    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Arjun"
    assert data["status"] == "new"
    assert data["id"] > 0


def test_list_leads(client):
    create_lead(client)
    create_lead(client, first_name="Priya", email="priya@example.com")

    response = client.get("/api/v1/leads?limit=1&offset=0")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["total"] == 2


def test_filter_leads_by_status(client):
    create_lead(client, status="new")
    create_lead(
        client,
        first_name="Qualified",
        email="qualified@example.com",
        status="qualified",
    )

    response = client.get("/api/v1/leads?status=qualified")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "qualified"


def test_filter_leads_by_company(client):
    company = create_company(client)
    create_lead(client, company_id=company["id"])
    create_lead(client)

    response = client.get(
        f"/api/v1/leads?company_id={company['id']}"
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_get_lead(client):
    created = create_lead(client).json()

    response = client.get(f"/api/v1/leads/{created['id']}")

    assert response.status_code == 200
    assert response.json()["email"] == "arjun@example.com"


def test_update_lead(client):
    created = create_lead(client).json()

    response = client.patch(
        f"/api/v1/leads/{created['id']}",
        json={"status": "qualified", "source": "referral"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "qualified"
    assert response.json()["source"] == "referral"


def test_empty_lead_update_returns_422(client):
    created = create_lead(client).json()

    response = client.patch(
        f"/api/v1/leads/{created['id']}",
        json={},
    )

    assert response.status_code == 422


def test_invalid_lead_status_returns_422(client):
    response = create_lead(client, status="invalid-status")
    assert response.status_code == 422


def test_missing_lead_returns_404(client):
    response = client.get("/api/v1/leads/999999999")
    assert response.status_code == 404


def test_lead_rejects_contact_from_another_company(client):
    company_a = create_company(client, "Company A")
    company_b = create_company(client, "Company B")
    contact = create_contact(client, company_id=company_a["id"])

    response = create_lead(
        client,
        company_id=company_b["id"],
        contact_id=contact["id"],
    )

    assert response.status_code == 422


def test_delete_lead(client):
    created = create_lead(client).json()
    lead_id = created["id"]

    response = client.delete(f"/api/v1/leads/{lead_id}")

    assert response.status_code == 204
    assert client.get(f"/api/v1/leads/{lead_id}").status_code == 404

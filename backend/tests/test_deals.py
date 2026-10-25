
def create_company(client, name="Deal Test Company"):
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
            "first_name": "Neha",
            "last_name": "Joshi",
            "email": "neha@example.com",
            "company_id": company_id,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_deal(client, **overrides):
    payload = {
        "name": "CRM Implementation",
        "amount": "250000.00",
        "stage": "qualification",
        "probability": 10,
        "expected_close_date": "2026-12-15",
        "description": "Initial discovery",
        "company_id": None,
        "contact_id": None,
    }
    payload.update(overrides)
    return client.post("/api/v1/deals", json=payload)


def test_create_deal(client):
    response = create_deal(client)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "CRM Implementation"
    assert data["probability"] == 10
    assert data["expected_close_date"] == "2026-12-15"


def test_list_deals(client):
    create_deal(client)
    create_deal(
        client,
        name="Second Deal",
        amount="50000.00",
    )

    response = client.get("/api/v1/deals?limit=1")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["total"] == 2


def test_filter_deals_by_stage(client):
    create_deal(client, stage="qualification")
    create_deal(
        client,
        name="Proposal Deal",
        stage="proposal",
    )

    response = client.get("/api/v1/deals?stage=proposal")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["stage"] == "proposal"


def test_filter_deals_by_amount(client):
    create_deal(client, amount="250000.00")
    create_deal(client, name="Small Deal", amount="50000.00")

    response = client.get(
        "/api/v1/deals?min_amount=100000&max_amount=300000"
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["name"] == "CRM Implementation"


def test_invalid_amount_filter_returns_422(client):
    response = client.get(
        "/api/v1/deals?min_amount=300000&max_amount=100000"
    )

    assert response.status_code == 422


def test_get_deal(client):
    created = create_deal(client).json()

    response = client.get(f"/api/v1/deals/{created['id']}")

    assert response.status_code == 200
    assert response.json()["name"] == "CRM Implementation"


def test_update_deal(client):
    created = create_deal(client).json()

    response = client.patch(
        f"/api/v1/deals/{created['id']}",
        json={
            "stage": "proposal",
            "probability": 60,
            "amount": "275000.00",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["stage"] == "proposal"
    assert data["probability"] == 60


def test_empty_deal_update_returns_422(client):
    created = create_deal(client).json()

    response = client.patch(
        f"/api/v1/deals/{created['id']}",
        json={},
    )

    assert response.status_code == 422


def test_probability_above_100_returns_422(client):
    response = create_deal(client, probability=120)
    assert response.status_code == 422


def test_negative_amount_returns_422(client):
    response = create_deal(client, amount="-100.00")
    assert response.status_code == 422


def test_invalid_deal_stage_returns_422(client):
    response = create_deal(client, stage="invalid-stage")
    assert response.status_code == 422


def test_missing_deal_returns_404(client):
    response = client.get("/api/v1/deals/999999999")
    assert response.status_code == 404


def test_deal_rejects_contact_from_another_company(client):
    company_a = create_company(client, "Company A")
    company_b = create_company(client, "Company B")
    contact = create_contact(client, company_id=company_a["id"])

    response = create_deal(
        client,
        company_id=company_b["id"],
        contact_id=contact["id"],
    )

    assert response.status_code == 422


def test_delete_deal(client):
    created = create_deal(client).json()
    deal_id = created["id"]

    response = client.delete(f"/api/v1/deals/{deal_id}")

    assert response.status_code == 204
    assert client.get(f"/api/v1/deals/{deal_id}").status_code == 404



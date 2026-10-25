
def create_company(client, name="Test Company"):
    return client.post(
        "/api/v1/companies",
        json={
            "name": name,
            "industry": "Technology",
            "website": "https://example.com",
            "employee_count": 25,
            "annual_revenue": "100000.00",
        },
    )


def test_create_company(client):
    response = create_company(client)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Company"
    assert data["id"] > 0


def test_list_companies(client):
    create_company(client, "Company A")
    create_company(client, "Company B")

    response = client.get("/api/v1/companies?limit=1&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["total"] == 2
    assert data["limit"] == 1
    assert data["offset"] == 0


def test_get_company(client):
    created = create_company(client).json()

    response = client.get(f"/api/v1/companies/{created['id']}")

    assert response.status_code == 200
    assert response.json()["name"] == "Test Company"


def test_update_company(client):
    created = create_company(client).json()

    response = client.patch(
        f"/api/v1/companies/{created['id']}",
        json={"industry": "Healthcare"},
    )

    assert response.status_code == 200
    assert response.json()["industry"] == "Healthcare"


def test_empty_company_update_returns_422(client):
    created = create_company(client).json()

    response = client.patch(
        f"/api/v1/companies/{created['id']}",
        json={},
    )

    assert response.status_code == 422


def test_missing_company_returns_404(client):
    response = client.get("/api/v1/companies/999999999")
    assert response.status_code == 404


def test_delete_company(client):
    created = create_company(client).json()
    company_id = created["id"]

    response = client.delete(f"/api/v1/companies/{company_id}")

    assert response.status_code == 204
    assert client.get(f"/api/v1/companies/{company_id}").status_code == 404


def test_invalid_company_input_returns_422(client):
    response = client.post(
        "/api/v1/companies",
        json={"name": "", "employee_count": -1},
    )

    assert response.status_code == 422

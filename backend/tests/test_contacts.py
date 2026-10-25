
def create_company(client):
    response = client.post(
        "/api/v1/companies",
        json={"name": "Contact Test Company"},
    )
    assert response.status_code == 201
    return response.json()


def create_contact(client, company_id=None):
    return client.post(
        "/api/v1/contacts",
        json={
            "first_name": "Aarav",
            "last_name": "Sharma",
            "email": "aarav@example.com",
            "phone": "9876543210",
            "title": "Account Manager",
            "company_id": company_id,
        },
    )


def test_create_contact(client):
    company = create_company(client)
    response = create_contact(client, company["id"])

    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Aarav"
    assert data["company_id"] == company["id"]


def test_list_contacts(client):
    create_contact(client)
    create_contact(client)

    response = client.get("/api/v1/contacts")

    assert response.status_code == 200
    assert response.json()["total"] == 2


def test_get_contact(client):
    created = create_contact(client).json()

    response = client.get(f"/api/v1/contacts/{created['id']}")

    assert response.status_code == 200
    assert response.json()["email"] == "aarav@example.com"


def test_update_contact(client):
    created = create_contact(client).json()

    response = client.patch(
        f"/api/v1/contacts/{created['id']}",
        json={"title": "Sales Director"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Sales Director"


def test_missing_contact_returns_404(client):
    response = client.get("/api/v1/contacts/999999999")
    assert response.status_code == 404


def test_contact_with_missing_company_returns_404(client):
    response = create_contact(client, company_id=999999999)
    assert response.status_code == 404


def test_invalid_contact_email_returns_422(client):
    response = client.post(
        "/api/v1/contacts",
        json={
            "first_name": "Aarav",
            "last_name": "Sharma",
            "email": "not-an-email",
        },
    )

    assert response.status_code == 422


def test_delete_contact(client):
    created = create_contact(client).json()
    contact_id = created["id"]

    response = client.delete(f"/api/v1/contacts/{contact_id}")

    assert response.status_code == 204
    assert client.get(f"/api/v1/contacts/{contact_id}").status_code == 404

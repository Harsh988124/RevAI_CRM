
def create_deal(client, name, expected_close_date=None):
    payload = {
        "name": name,
        "amount": "100000.00",
        "stage": "qualification",
        "probability": 50,
    }

    if expected_close_date is not None:
        payload["expected_close_date"] = expected_close_date

    response = client.post("/api/v1/deals", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_policy(client, **overrides):
    payload = {
        "policy_key": "proposal_requirements",
        "name": "Proposal requirements",
        "description": "Required fields before proposal stage",
        "from_stage": "qualification",
        "to_stage": "proposal",
        "required_fields": ["expected_close_date"],
        "min_amount": None,
        "min_probability": None,
        "require_open_task": False,
    }
    payload.update(overrides)

    response = client.post("/api/v1/policies", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def activate_policy(client, policy_id):
    response = client.post(
        f"/api/v1/policies/{policy_id}/activate"
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_create_policy_starts_as_draft(client):
    policy = create_policy(client)

    assert policy["version"] == 1
    assert policy["policy_key"] == "proposal_requirements"
    assert policy["is_active"] is False


def test_same_key_creates_new_version(client):
    first = create_policy(client)

    second = create_policy(
        client,
        name="Proposal requirements v2",
        min_probability=40,
    )

    assert second["policy_key"] == first["policy_key"]
    assert second["version"] == 2
    assert second["is_active"] is False

    # Creating a new version must not modify the old version.
    first_response = client.get(
        f"/api/v1/policies/{first['id']}"
    )
    assert first_response.status_code == 200
    assert first_response.json()["version"] == 1
    assert first_response.json()["min_probability"] is None


def test_only_one_version_per_policy_key_is_active(client):
    first = create_policy(client)
    second = create_policy(
        client,
        name="Proposal requirements v2",
    )

    activate_policy(client, first["id"])
    activate_policy(client, second["id"])

    response = client.get(
        "/api/v1/policies",
        params={
            "policy_key": "proposal_requirements",
            "active_only": True,
        },
    )

    assert response.status_code == 200
    active = response.json()["items"]

    assert len(active) == 1
    assert active[0]["id"] == second["id"]


def test_draft_policy_does_not_block_transition(client):
    deal = create_deal(client, "Draft Policy Deal")
    create_policy(client)  # Deliberately not activated.

    response = client.patch(
        f"/api/v1/deals/{deal['id']}",
        json={"stage": "proposal"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["stage"] == "proposal"


def test_active_policy_blocks_missing_close_date(client):
    deal = create_deal(client, "Missing Close Date Deal")
    policy = create_policy(client)
    activate_policy(client, policy["id"])

    response = client.patch(
        f"/api/v1/deals/{deal['id']}",
        json={"stage": "proposal"},
    )

    assert response.status_code == 409

    detail = response.json()["detail"]
    assert detail["message"] == (
        "Deal stage transition blocked by sales policies"
    )
    assert any(
        item["code"] == "missing_required_field"
        and item["field"] == "expected_close_date"
        for item in detail["violations"]
    )

    # A blocked attempt must not change the deal stage.
    current = client.get(f"/api/v1/deals/{deal['id']}")
    assert current.status_code == 200
    assert current.json()["stage"] == "qualification"

    # The blocked evaluation must be preserved for audit.
    evaluations = client.get(
        "/api/v1/policies/evaluations",
        params={"deal_id": deal["id"], "status": "blocked"},
    )

    assert evaluations.status_code == 200
    assert evaluations.json()["total"] == 1


def test_valid_deal_can_transition(client):
    deal = create_deal(
        client,
        "Complete Deal",
        expected_close_date="2027-06-30",
    )
    policy = create_policy(client)
    activate_policy(client, policy["id"])

    response = client.patch(
        f"/api/v1/deals/{deal['id']}",
        json={"stage": "proposal"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["stage"] == "proposal"

    evaluations = client.get(
        "/api/v1/policies/evaluations",
        params={"deal_id": deal["id"], "status": "allowed"},
    )

    assert evaluations.status_code == 200
    assert evaluations.json()["total"] == 1
    assert evaluations.json()["items"][0]["violations"] == []


def test_policy_simulation_does_not_change_deals(client):
    missing_date_deal = create_deal(
        client,
        "Missing Date",
    )
    complete_deal = create_deal(
        client,
        "Complete Deal",
        expected_close_date="2027-06-30",
    )
    policy = create_policy(client)

    response = client.post(
        f"/api/v1/policies/{policy['id']}/simulate"
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["candidate_count"] == 2
    assert data["passing_count"] == 1
    assert data["failing_count"] == 1

    by_id = {item["deal_id"]: item for item in data["results"]}

    assert by_id[missing_date_deal["id"]]["would_pass"] is False
    assert by_id[complete_deal["id"]]["would_pass"] is True

    # Simulation must not alter either deal's actual stage.
    first = client.get(
        f"/api/v1/deals/{missing_date_deal['id']}"
    ).json()
    second = client.get(
        f"/api/v1/deals/{complete_deal['id']}"
    ).json()

    assert first["stage"] == "qualification"
    assert second["stage"] == "qualification"


def test_policy_can_require_an_open_task(client):
    deal = create_deal(
        client,
        "Task Required Deal",
        expected_close_date="2027-06-30",
    )

    policy = create_policy(
        client,
        require_open_task=True,
    )
    activate_policy(client, policy["id"])

    blocked = client.patch(
        f"/api/v1/deals/{deal['id']}",
        json={"stage": "proposal"},
    )

    assert blocked.status_code == 409
    assert any(
        item["code"] == "missing_open_task"
        for item in blocked.json()["detail"]["violations"]
    )


def test_missing_policy_returns_404(client):
    response = client.get("/api/v1/policies/999999999")
    assert response.status_code == 404


def test_invalid_policy_field_returns_422(client):
    response = client.post(
        "/api/v1/policies",
        json={
            "policy_key": "invalid_policy",
            "name": "Invalid field policy",
            "to_stage": "proposal",
            "required_fields": ["password"],
        },
    )

    assert response.status_code == 422

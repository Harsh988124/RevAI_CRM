
def create_deal(client):
    response = client.post(
        "/api/v1/deals",
        json={
            "name": "Override Test Deal",
            "amount": "100000.00",
            "stage": "qualification",
            "probability": 10,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_and_activate_policy(client):
    response = client.post(
        "/api/v1/policies",
        json={
            "policy_key": "override_test_policy",
            "name": "Proposal Contact Requirement",
            "description": "Require a contact before Proposal.",
            "from_stage": "qualification",
            "to_stage": "proposal",
            "required_fields": ["contact_id"],
            "min_amount": None,
            "min_probability": None,
            "require_open_task": False,
        },
    )
    assert response.status_code == 201, response.text

    policy = response.json()

    activation = client.post(
        f"/api/v1/policies/{policy['id']}/activate"
    )
    assert activation.status_code == 200, activation.text

    return policy


def test_transition_without_reason_is_blocked(client):
    deal = create_deal(client)
    create_and_activate_policy(client)

    response = client.post(
        f"/api/v1/deals/{deal['id']}/transition",
        json={"target_stage": "proposal"},
    )

    assert response.status_code == 409

    current = client.get(f"/api/v1/deals/{deal['id']}")
    assert current.status_code == 200
    assert current.json()["stage"] == "qualification"

    evaluations = client.get(
        "/api/v1/policies/evaluations",
        params={
            "deal_id": deal["id"],
            "status": "blocked",
        },
    )

    assert evaluations.status_code == 200
    assert evaluations.json()["total"] == 1


def test_manager_can_override_with_reason(client):
    deal = create_deal(client)
    policy = create_and_activate_policy(client)

    response = client.post(
        f"/api/v1/deals/{deal['id']}/transition",
        json={
            "target_stage": "proposal",
            "override_reason": (
                "Strategic exception approved by sales management."
            ),
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["stage"] == "proposal"

    evaluations = client.get(
        "/api/v1/policies/evaluations",
        params={
            "deal_id": deal["id"],
            "status": "overridden",
        },
    )

    assert evaluations.status_code == 200
    assert evaluations.json()["total"] == 1

    audit = evaluations.json()["items"][0]

    assert audit["override_reason"] == (
        "Strategic exception approved by sales management."
    )
    assert audit["evaluated_by"] == "test-manager@example.com"
    assert audit["policy_versions"][0]["policy_id"] == policy["id"]


def test_override_reason_must_not_be_blank(client):
    deal = create_deal(client)
    create_and_activate_policy(client)

    response = client.post(
        f"/api/v1/deals/{deal['id']}/transition",
        json={
            "target_stage": "proposal",
            "override_reason": "          ",
        },
    )

    assert response.status_code == 422

    current = client.get(f"/api/v1/deals/{deal['id']}")
    assert current.json()["stage"] == "qualification"


def test_missing_deal_transition_returns_404(client):
    response = client.post(
        "/api/v1/deals/999999999/transition",
        json={"target_stage": "proposal"},
    )

    assert response.status_code == 404


def test_transition_to_same_stage_returns_422(client):
    deal = create_deal(client)

    response = client.post(
        f"/api/v1/deals/{deal['id']}/transition",
        json={"target_stage": "qualification"},
    )

    assert response.status_code == 422

def create_deal(client):
    response = client.post(
        "/api/v1/deals",
        json={
            "name": "Override Test Deal",
            "amount": "100000.00",
            "stage": "qualification",
            "probability": 10,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_and_activate_policy(client):
    response = client.post(
        "/api/v1/policies",
        json={
            "policy_key": "override_test_policy",
            "name": "Proposal Contact Requirement",
            "description": "Require a contact before Proposal.",
            "from_stage": "qualification",
            "to_stage": "proposal",
            "required_fields": ["contact_id"],
            "min_amount": None,
            "min_probability": None,
            "require_open_task": False,
        },
    )
    assert response.status_code == 201, response.text

    policy = response.json()

    activation = client.post(
        f"/api/v1/policies/{policy['id']}/activate"
    )
    assert activation.status_code == 200, activation.text

    return policy


def test_transition_without_reason_is_blocked(client):
    deal = create_deal(client)
    create_and_activate_policy(client)

    response = client.post(
        f"/api/v1/deals/{deal['id']}/transition",
        json={"target_stage": "proposal"},
    )

    assert response.status_code == 409

    current = client.get(f"/api/v1/deals/{deal['id']}")
    assert current.status_code == 200
    assert current.json()["stage"] == "qualification"

    evaluations = client.get(
        "/api/v1/policies/evaluations",
        params={
            "deal_id": deal["id"],
            "status": "blocked",
        },
    )

    assert evaluations.status_code == 200
    assert evaluations.json()["total"] == 1


def test_manager_can_override_with_reason(client):
    deal = create_deal(client)
    policy = create_and_activate_policy(client)

    response = client.post(
        f"/api/v1/deals/{deal['id']}/transition",
        json={
            "target_stage": "proposal",
            "override_reason": (
                "Strategic exception approved by sales management."
            ),
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["stage"] == "proposal"

    evaluations = client.get(
        "/api/v1/policies/evaluations",
        params={
            "deal_id": deal["id"],
            "status": "overridden",
        },
    )

    assert evaluations.status_code == 200
    assert evaluations.json()["total"] == 1

    audit = evaluations.json()["items"][0]

    assert audit["override_reason"] == (
        "Strategic exception approved by sales management."
    )
    assert audit["evaluated_by"] == "test-manager@example.com"
    assert audit["policy_versions"][0]["policy_id"] == policy["id"]


def test_override_reason_must_not_be_blank(client):
    deal = create_deal(client)
    create_and_activate_policy(client)

    response = client.post(
        f"/api/v1/deals/{deal['id']}/transition",
        json={
            "target_stage": "proposal",
            "override_reason": "          ",
        },
    )

    assert response.status_code == 422

    current = client.get(f"/api/v1/deals/{deal['id']}")
    assert current.json()["stage"] == "qualification"


def test_missing_deal_transition_returns_404(client):
    response = client.post(
        "/api/v1/deals/999999999/transition",
        json={"target_stage": "proposal"},
    )

    assert response.status_code == 404


def test_transition_to_same_stage_returns_422(client):
    deal = create_deal(client)

    response = client.post(
        f"/api/v1/deals/{deal['id']}/transition",
        json={"target_stage": "qualification"},
    )

    assert response.status_code == 422


def create_deal(client):
    response = client.post(
        "/api/v1/deals",
        json={
            "name": "Stage History Test Deal",
            "amount": "100000.00",
            "stage": "qualification",
            "probability": 10,
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def test_new_deal_records_initial_stage(client):
    deal = create_deal(client)

    response = client.get(
        f"/api/v1/deals/{deal['id']}/history"
    )

    assert response.status_code == 200

    history = response.json()

    assert len(history) == 1
    assert history[0]["from_stage"] is None
    assert history[0]["to_stage"] == "qualification"
    assert history[0]["deal_id"] == deal["id"]


def test_stage_change_records_previous_and_new_stage(client):
    deal = create_deal(client)
    deal_id = deal["id"]

    update_response = client.patch(
        f"/api/v1/deals/{deal_id}",
        json={"stage": "discovery"},
    )

    assert update_response.status_code == 200, update_response.text

    response = client.get(
        f"/api/v1/deals/{deal_id}/history"
    )

    assert response.status_code == 200

    history = response.json()

    assert len(history) == 2

    assert history[0]["from_stage"] is None
    assert history[0]["to_stage"] == "qualification"

    assert history[1]["from_stage"] == "qualification"
    assert history[1]["to_stage"] == "discovery"


def test_updating_amount_does_not_add_stage_history(client):
    deal = create_deal(client)

    update_response = client.patch(
        f"/api/v1/deals/{deal['id']}",
        json={"amount": "125000.00"},
    )

    assert update_response.status_code == 200, update_response.text

    response = client.get(
        f"/api/v1/deals/{deal['id']}/history"
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_repeated_same_stage_does_not_add_history(client):
    deal = create_deal(client)

    update_response = client.patch(
        f"/api/v1/deals/{deal['id']}",
        json={"stage": "qualification"},
    )

    assert update_response.status_code == 200, update_response.text

    response = client.get(
        f"/api/v1/deals/{deal['id']}/history"
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_missing_deal_history_returns_404(client):
    response = client.get(
        "/api/v1/deals/999999999/history"
    )

    assert response.status_code == 404


from datetime import datetime, timedelta, timezone

import app.services.revenue_intelligence as intelligence_service


def create_task(client, **overrides):
    payload = {
        "title": "Follow up with prospect",
        "description": "Send the proposal",
        "status": "todo",
        "priority": "high",
        "due_at": "2020-01-01T00:00:00Z",
    }
    payload.update(overrides)

    response = client.post("/api/v1/tasks", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_deal(client, **overrides):
    payload = {
        "name": "Revenue Intelligence Test Deal",
        "amount": "100000.00",
        "stage": "proposal",
        "probability": 60,
        "expected_close_date": "2020-01-01",
    }
    payload.update(overrides)

    response = client.post("/api/v1/deals", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_lead(client):
    response = client.post(
        "/api/v1/leads",
        json={
            "first_name": "Test",
            "last_name": "Prospect",
            "email": "prospect@example.com",
            "status": "new",
            "source": "website",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def run_scan(client, **params):
    response = client.post("/api/v1/intelligence/run", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def get_findings(client, **params):
    response = client.get("/api/v1/intelligence/findings", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_overdue_task_creates_finding(client):
    create_task(client)

    run_scan(client)

    result = get_findings(client, rule_code="overdue_task")

    assert result["total"] == 1
    assert result["items"][0]["entity_type"] == "task"
    assert result["items"][0]["severity"] == "high"
    assert result["items"][0]["status"] == "open"


def test_past_close_date_creates_finding(client):
    create_deal(client)

    run_scan(client)

    result = get_findings(client, rule_code="deal_past_close_date")

    assert result["total"] == 1
    assert result["items"][0]["entity_type"] == "deal"
    assert result["items"][0]["evidence"]["days_past_close"] > 0


def test_repeated_scans_do_not_duplicate_findings(client):
    create_task(client)

    run_scan(client)
    run_scan(client)

    result = get_findings(client, rule_code="overdue_task")

    assert result["total"] == 1


def test_completed_task_resolves_overdue_finding(client):
    task = create_task(client)
    run_scan(client)

    update = client.patch(
        f"/api/v1/tasks/{task['id']}",
        json={"status": "completed"},
    )
    assert update.status_code == 200, update.text

    run_scan(client)

    result = get_findings(
        client,
        status="resolved",
        rule_code="overdue_task",
    )

    assert result["total"] == 1


def test_dismissed_finding_stays_dismissed(client):
    create_task(client)
    run_scan(client)

    result = get_findings(client, rule_code="overdue_task")
    finding_id = result["items"][0]["id"]

    response = client.post(
        f"/api/v1/intelligence/findings/{finding_id}/dismiss",
        json={"reason": "Reviewed with the sales manager"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "dismissed"

    # A repeated scan must not reopen a dismissed finding.
    run_scan(client)

    result = get_findings(
        client,
        status="dismissed",
        rule_code="overdue_task",
    )
    assert result["total"] == 1


def test_lead_without_followup_creates_finding(client, monkeypatch):
    create_lead(client)

    future_time = datetime.now(timezone.utc) + timedelta(days=5)
    monkeypatch.setattr(
        intelligence_service,
        "utc_now",
        lambda: future_time,
    )

    run_scan(client, lead_followup_days=3)

    result = get_findings(client, rule_code="lead_no_follow_up")

    assert result["total"] == 1
    assert result["items"][0]["entity_type"] == "lead"


def test_stalled_deal_and_missing_next_step_rules(client, monkeypatch):
    create_deal(
        client,
        expected_close_date="2027-12-31",
    )

    future_time = datetime.now(timezone.utc) + timedelta(days=20)
    monkeypatch.setattr(
        intelligence_service,
        "utc_now",
        lambda: future_time,
    )

    run_scan(
        client,
        stalled_days=14,
        inactive_days=14,
        next_step_days=3,
    )

    stalled = get_findings(client, rule_code="deal_stalled")
    missing_next_step = get_findings(
        client,
        rule_code="deal_missing_next_step",
    )
    inactive = get_findings(client, rule_code="deal_inactive")

    assert stalled["total"] == 1
    assert missing_next_step["total"] == 1
    assert inactive["total"] == 1


def test_intelligence_summary(client):
    create_task(client)
    run_scan(client)

    response = client.get("/api/v1/intelligence/summary")

    assert response.status_code == 200
    summary = response.json()
    assert summary["open_findings"] >= 1
    assert summary["by_severity"]["high"] >= 1
    assert summary["by_rule"]["overdue_task"] == 1


def test_missing_finding_returns_404(client):
    response = client.get("/api/v1/intelligence/findings/999999999")
    assert response.status_code == 404


def test_dismissing_missing_finding_returns_404(client):
    response = client.post(
        "/api/v1/intelligence/findings/999999999/dismiss",
        json={"reason": "Reviewed and not applicable"},
    )
    assert response.status_code == 404

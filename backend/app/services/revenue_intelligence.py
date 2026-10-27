
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    Activity,
    Deal,
    DealStageHistory,
    Lead,
    RevenueFinding,
    Task,
)


CLOSED_DEAL_STAGES = {"closed_won", "closed_lost"}
OPEN_TASK_STATUSES = {"todo", "in_progress"}
ACTIVE_LEAD_STATUSES = {"new", "contacted", "qualified"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None

    if value.tzinfo is None:
        # Treat legacy timestamps without a timezone as UTC.
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def age_in_days(value: datetime, now: datetime) -> float:
    normalized = as_utc(value)
    assert normalized is not None
    return max(0.0, (now - normalized).total_seconds() / 86400)


def make_finding(
    *,
    rule_code: str,
    entity_type: str,
    entity_id: int,
    title: str,
    description: str,
    recommendation: str,
    severity: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "fingerprint": f"{rule_code}:{entity_type}:{entity_id}",
        "rule_code": rule_code,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "title": title[:200],
        "description": description,
        "recommendation": recommendation,
        "severity": severity,
        "evidence": evidence,
    }


def scan_revenue_intelligence(
    db: Session,
    *,
    stalled_days: int = 14,
    inactive_days: int = 14,
    lead_followup_days: int = 3,
    next_step_days: int = 3,
) -> dict[str, Any]:
    now = utc_now()
    today = now.date()

    tasks = db.query(Task).all()
    activities = db.query(Activity).all()
    deals = db.query(Deal).all()
    leads = db.query(Lead).all()
    stage_history = db.query(DealStageHistory).all()

    candidates: dict[str, dict[str, Any]] = {}

    def add(candidate: dict[str, Any]) -> None:
        candidates[candidate["fingerprint"]] = candidate

    # Index the latest stage transition and activity for each deal.
    latest_stage_change: dict[int, datetime] = {}
    for entry in stage_history:
        changed_at = as_utc(entry.changed_at)
        if changed_at is None:
            continue

        current = latest_stage_change.get(entry.deal_id)
        if current is None or changed_at > current:
            latest_stage_change[entry.deal_id] = changed_at

    latest_deal_activity: dict[int, datetime] = {}
    for activity in activities:
        if activity.deal_id is None:
            continue

        occurred_at = as_utc(activity.occurred_at)
        if occurred_at is None:
            continue

        current = latest_deal_activity.get(activity.deal_id)
        if current is None or occurred_at > current:
            latest_deal_activity[activity.deal_id] = occurred_at

    # Track leads which have at least one task or activity.
    followed_lead_ids: set[int] = set()
    followed_contact_ids: set[int] = set()

    for task in tasks:
        if task.lead_id is not None:
            followed_lead_ids.add(task.lead_id)
        if task.contact_id is not None:
            followed_contact_ids.add(task.contact_id)

    for activity in activities:
        if activity.lead_id is not None:
            followed_lead_ids.add(activity.lead_id)
        if activity.contact_id is not None:
            followed_contact_ids.add(activity.contact_id)

    # Rule 1: overdue open tasks.
    for task in tasks:
        due_at = as_utc(task.due_at)

        if (
            task.status not in OPEN_TASK_STATUSES
            or due_at is None
            or due_at >= now
        ):
            continue

        overdue_days = int((now - due_at).total_seconds() // 86400)

        severity = (
            "critical"
            if task.priority == "urgent"
            else "high"
            if task.priority == "high" or overdue_days >= 7
            else "medium"
            if task.priority == "medium"
            else "low"
        )

        add(
            make_finding(
                rule_code="overdue_task",
                entity_type="task",
                entity_id=task.id,
                title=f"Overdue task: {task.title}",
                description=(
                    f"This task was due at {due_at.isoformat()} "
                    f"and is still marked '{task.status}'."
                ),
                recommendation=(
                    "Complete the follow-up or update its due date and status."
                ),
                severity=severity,
                evidence={
                    "due_at": due_at.isoformat(),
                    "status": task.status,
                    "priority": task.priority,
                    "overdue_days": overdue_days,
                    "company_id": task.company_id,
                    "deal_id": task.deal_id,
                    "lead_id": task.lead_id,
                },
            )
        )

    active_deals = [
        deal for deal in deals if deal.stage not in CLOSED_DEAL_STAGES
    ]

    # Track deals with an active, deal-specific next-step task.
    deals_with_open_tasks = {
        task.deal_id
        for task in tasks
        if task.deal_id is not None
        and task.status in OPEN_TASK_STATUSES
    }

    # Rule 2: expected close date has passed.
    for deal in active_deals:
        close_date = deal.expected_close_date

        if close_date is None or close_date >= today:
            continue

        days_past_close = (today - close_date).days

        add(
            make_finding(
                rule_code="deal_past_close_date",
                entity_type="deal",
                entity_id=deal.id,
                title=f"Deal past close date: {deal.name}",
                description=(
                    f"The expected close date was {close_date.isoformat()}, "
                    f"{days_past_close} day(s) ago. The deal is still open."
                ),
                recommendation=(
                    "Review the forecast, update the expected close date, "
                    "and verify the next customer commitment."
                ),
                severity="high" if days_past_close >= 14 else "medium",
                evidence={
                    "expected_close_date": close_date.isoformat(),
                    "days_past_close": days_past_close,
                    "stage": deal.stage,
                    "amount": str(deal.amount) if deal.amount is not None else None,
                },
            )
        )

    # Rules 3–5: stalled deals, inactivity, and missing next steps.
    for deal in active_deals:
        stage_since = latest_stage_change.get(deal.id)
        if stage_since is None:
            stage_since = as_utc(deal.created_at)

        if stage_since is not None:
            days_in_stage = age_in_days(stage_since, now)

            # Rule 3: stage has not changed for too long.
            if days_in_stage >= stalled_days:
                add(
                    make_finding(
                        rule_code="deal_stalled",
                        entity_type="deal",
                        entity_id=deal.id,
                        title=f"Stalled deal: {deal.name}",
                        description=(
                            f"The deal has remained in '{deal.stage}' for "
                            f"approximately {int(days_in_stage)} day(s)."
                        ),
                        recommendation=(
                            "Review the latest interaction, identify the blocker, "
                            "and agree on a concrete next step."
                        ),
                        severity=(
                            "high"
                            if days_in_stage >= stalled_days * 2
                            else "medium"
                        ),
                        evidence={
                            "stage": deal.stage,
                            "stage_since": stage_since.isoformat(),
                            "days_in_stage": int(days_in_stage),
                            "threshold_days": stalled_days,
                        },
                    )
                )

            # Rule 5: no active task for this deal.
            if (
                days_in_stage >= next_step_days
                and deal.id not in deals_with_open_tasks
            ):
                add(
                    make_finding(
                        rule_code="deal_missing_next_step",
                        entity_type="deal",
                        entity_id=deal.id,
                        title=f"Missing next step: {deal.name}",
                        description=(
                            "This open deal has no task in a to-do or "
                            "in-progress state linked directly to it."
                        ),
                        recommendation=(
                            "Create a dated follow-up task with a clear owner "
                            "and customer-facing objective."
                        ),
                        severity="medium",
                        evidence={
                            "stage": deal.stage,
                            "stage_since": stage_since.isoformat(),
                            "days_in_stage": int(days_in_stage),
                            "open_task_count": 0,
                        },
                    )
                )

        # Rule 4: no recent activity recorded directly against the deal.
        latest_activity = latest_deal_activity.get(deal.id)

        # Use deal creation time when no activity has ever been logged.
        activity_reference = (
            latest_activity
            if latest_activity is not None
            else as_utc(deal.created_at)
        )

        if activity_reference is not None:
            days_without_activity = age_in_days(activity_reference, now)

            if days_without_activity >= inactive_days:
                add(
                    make_finding(
                        rule_code="deal_inactive",
                        entity_type="deal",
                        entity_id=deal.id,
                        title=f"No recent activity: {deal.name}",
                        description=(
                            "No activity has been logged against this deal "
                            f"for approximately {int(days_without_activity)} day(s)."
                        ),
                        recommendation=(
                            "Review customer engagement and log the latest "
                            "call, email, meeting, or outcome."
                        ),
                        severity=(
                            "high"
                            if days_without_activity >= inactive_days * 2
                            else "medium"
                        ),
                        evidence={
                            "last_activity_at": (
                                latest_activity.isoformat()
                                if latest_activity is not None
                                else None
                            ),
                            "reference_at": activity_reference.isoformat(),
                            "days_without_activity": int(days_without_activity),
                            "threshold_days": inactive_days,
                        },
                    )
                )

    # Rule 6: leads with no task or activity after the grace period.
    for lead in leads:
        if lead.status not in ACTIVE_LEAD_STATUSES:
            continue

        created_at = as_utc(lead.created_at)
        if created_at is None:
            continue

        days_since_created = age_in_days(created_at, now)

        if days_since_created < lead_followup_days:
            continue

        has_followup = (
            lead.id in followed_lead_ids
            or (
                lead.contact_id is not None
                and lead.contact_id in followed_contact_ids
            )
        )

        if has_followup:
            continue

        add(
            make_finding(
                rule_code="lead_no_follow_up",
                entity_type="lead",
                entity_id=lead.id,
                title=f"Lead has no follow-up: {lead.first_name} {lead.last_name}",
                description=(
                    f"This lead has been in the CRM for "
                    f"{int(days_since_created)} day(s) without a task or "
                    "activity linked to the lead or its associated contact."
                ),
                recommendation=(
                    "Schedule a first-touch task and record the outcome "
                    "of the outreach."
                ),
                severity=(
                    "high"
                    if days_since_created >= lead_followup_days * 3
                    else "medium"
                ),
                evidence={
                    "lead_status": lead.status,
                    "created_at": created_at.isoformat(),
                    "days_since_created": int(days_since_created),
                    "threshold_days": lead_followup_days,
                    "company_id": lead.company_id,
                    "contact_id": lead.contact_id,
                },
            )
        )

    # Deduplicate existing records and reconcile this scan.
    existing_records = db.query(RevenueFinding).all()
    existing_by_fingerprint = {
        finding.fingerprint: finding for finding in existing_records
    }

    created_count = 0
    updated_count = 0
    resolved_count = 0

    try:
        for fingerprint, candidate in candidates.items():
            existing = existing_by_fingerprint.get(fingerprint)

            if existing is None:
                db.add(
                    RevenueFinding(
                        **candidate,
                        status="open",
                        first_detected_at=now,
                        last_detected_at=now,
                    )
                )
                created_count += 1
                continue

            if existing.status == "dismissed":
                # Respect a user's explicit dismissal.
                existing.last_detected_at = now
                existing.evidence = candidate["evidence"]
                continue

            if existing.status == "resolved":
                # Reopen if the underlying problem has returned.
                existing.status = "open"
                existing.first_detected_at = now
                existing.resolved_at = None
                existing.disposition_reason = None

            existing.title = candidate["title"]
            existing.description = candidate["description"]
            existing.recommendation = candidate["recommendation"]
            existing.severity = candidate["severity"]
            existing.evidence = candidate["evidence"]
            existing.last_detected_at = now
            updated_count += 1

        # If an open finding was not reproduced, automatically resolve it.
        for existing in existing_records:
            if (
                existing.status == "open"
                and existing.fingerprint not in candidates
            ):
                existing.status = "resolved"
                existing.resolved_at = now
                resolved_count += 1

        db.commit()

    except Exception:
        db.rollback()
        raise

    open_count = (
        db.query(RevenueFinding)
        .filter(RevenueFinding.status == "open")
        .count()
    )

    return {
        "scanned_at": now,
        "findings_created": created_count,
        "findings_updated": updated_count,
        "findings_resolved": resolved_count,
        "open_findings": open_count,
        "entities_scanned": {
            "tasks": len(tasks),
            "activities": len(activities),
            "deals": len(deals),
            "leads": len(leads),
        },
    }

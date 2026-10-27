
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Deal, SalesPolicyVersion, Task


OPEN_TASK_STATUSES = ("todo", "in_progress")


def evaluate_policy_for_deal(
    db: Session,
    policy: SalesPolicyVersion,
    deal: Deal,
) -> list[dict]:
    """
    Evaluate one policy against the current state of a deal.
    This function does not modify the deal or the policy.
    """
    violations: list[dict] = []

    def add_violation(
        code: str,
        field: str | None,
        message: str,
    ) -> None:
        violations.append(
            {
                "policy_id": policy.id,
                "policy_key": policy.policy_key,
                "policy_version": policy.version,
                "code": code,
                "field": field,
                "message": message,
            }
        )

    # Check mandatory CRM fields.
    for field in policy.required_fields or []:
        value = getattr(deal, field, None)

        missing = value is None
        if isinstance(value, str) and not value.strip():
            missing = True

        if missing:
            add_violation(
                code="missing_required_field",
                field=field,
                message=(
                    f"Field '{field}' must be populated before moving "
                    f"the deal to '{policy.to_stage}'."
                ),
            )

    # Check minimum monetary amount, when configured.
    if policy.min_amount is not None:
        if deal.amount is None or deal.amount < policy.min_amount:
            add_violation(
                code="minimum_amount_not_met",
                field="amount",
                message=(
                    f"Deal amount must be at least {policy.min_amount} "
                    "to satisfy this policy."
                ),
            )

    # Check minimum probability, when configured.
    if policy.min_probability is not None:
        if (
            deal.probability is None
            or deal.probability < policy.min_probability
        ):
            add_violation(
                code="minimum_probability_not_met",
                field="probability",
                message=(
                    f"Deal probability must be at least "
                    f"{policy.min_probability}% to satisfy this policy."
                ),
            )

    # Require a directly linked, open follow-up task.
    if policy.require_open_task:
        has_open_task = (
            db.query(Task.id)
            .filter(
                Task.deal_id == deal.id,
                Task.status.in_(OPEN_TASK_STATUSES),
            )
            .first()
            is not None
        )

        if not has_open_task:
            add_violation(
                code="missing_open_task",
                field="tasks",
                message=(
                    "At least one to-do or in-progress task linked "
                    "directly to this deal is required."
                ),
            )

    return violations


def get_applicable_active_policies(
    db: Session,
    deal: Deal,
    target_stage: str,
) -> list[SalesPolicyVersion]:
    """
    Retrieve active policies that apply to this exact transition.

    A policy with from_stage=None applies from any current stage,
    while a specified from_stage applies only to that stage.
    """
    return (
        db.query(SalesPolicyVersion)
        .filter(
            SalesPolicyVersion.is_active.is_(True),
            SalesPolicyVersion.to_stage == target_stage,
            or_(
                SalesPolicyVersion.from_stage.is_(None),
                SalesPolicyVersion.from_stage == deal.stage,
            ),
        )
        .order_by(
            SalesPolicyVersion.policy_key.asc(),
            SalesPolicyVersion.version.desc(),
        )
        .all()
    )


def evaluate_active_policies(
    db: Session,
    deal: Deal,
    target_stage: str,
) -> tuple[list[SalesPolicyVersion], list[dict]]:
    policies = get_applicable_active_policies(
        db,
        deal,
        target_stage,
    )

    violations: list[dict] = []

    for policy in policies:
        violations.extend(
            evaluate_policy_for_deal(db, policy, deal)
        )

    return policies, violations

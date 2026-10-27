
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import (
    Company,
    Contact,
    Deal,
    DealStageHistory,
    PolicyEvaluation,
)
from app.schemas.deal import (
    DealCreate,
    DealListResponse,
    DealResponse,
    DealUpdate,
)
from app.schemas.deal_history import DealStageHistoryResponse
from app.services.policy_engine import evaluate_active_policies
from app.api.dependencies import get_current_user
from app.models import User
from app.schemas.deal_transition import DealTransitionRequest

router = APIRouter(prefix="/deals", tags=["Deals"])


def validate_relationships(
    db: Session,
    company_id: int | None,
    contact_id: int | None,
) -> None:
    """Validate company and contact references before saving a deal."""

    company = (
        db.get(Company, company_id)
        if company_id is not None
        else None
    )

    contact = (
        db.get(Contact, contact_id)
        if contact_id is not None
        else None
    )

    if company_id is not None and company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    if contact_id is not None and contact is None:
        raise HTTPException(
            status_code=404,
            detail="Contact not found",
        )

    if (
        company_id is not None
        and contact is not None
        and contact.company_id is not None
        and contact.company_id != company_id
    ):
        raise HTTPException(
            status_code=422,
            detail="Contact does not belong to the specified company",
        )


@router.post("", response_model=DealResponse, status_code=201)
def create_deal(
    payload: DealCreate,
    db: Session = Depends(get_db),
):
    """Create a deal and record its initial stage."""

    data = payload.model_dump()

    validate_relationships(
        db,
        company_id=data.get("company_id"),
        contact_id=data.get("contact_id"),
    )

    deal = Deal(**data)
    db.add(deal)

    try:
        # Generate the deal ID without committing yet.
        db.flush()

        # Record the initial stage in the same transaction.
        db.add(
            DealStageHistory(
                deal_id=deal.id,
                from_stage=None,
                to_stage=deal.stage,
            )
        )

        db.commit()
        db.refresh(deal)

    except Exception:
        db.rollback()
        raise

    return deal


@router.get("", response_model=DealListResponse)
def list_deals(
    db: Session = Depends(get_db),
    stage: str | None = None,
    company_id: int | None = Query(default=None, gt=0),
    min_amount: Decimal | None = Query(default=None, ge=0),
    max_amount: Decimal | None = Query(default=None, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List deals with pagination and optional filters."""

    if (
        min_amount is not None
        and max_amount is not None
        and min_amount > max_amount
    ):
        raise HTTPException(
            status_code=422,
            detail="min_amount cannot be greater than max_amount",
        )

    filters = []

    if stage is not None:
        filters.append(Deal.stage == stage)

    if company_id is not None:
        filters.append(Deal.company_id == company_id)

    if min_amount is not None:
        filters.append(Deal.amount >= min_amount)

    if max_amount is not None:
        filters.append(Deal.amount <= max_amount)

    query = db.query(Deal).filter(*filters)

    total = (
        db.query(func.count(Deal.id))
        .filter(*filters)
        .scalar()
        or 0
    )

    items = (
        query.order_by(Deal.created_at.desc(), Deal.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/{deal_id}/history",
    response_model=list[DealStageHistoryResponse],
)
def get_deal_stage_history(
    deal_id: int,
    db: Session = Depends(get_db),
):
    """Return the stage history for a deal in chronological order."""

    deal = db.get(Deal, deal_id)

    if deal is None:
        raise HTTPException(
            status_code=404,
            detail="Deal not found",
        )

    return (
        db.query(DealStageHistory)
        .filter(DealStageHistory.deal_id == deal_id)
        .order_by(
            DealStageHistory.changed_at.asc(),
            DealStageHistory.id.asc(),
        )
        .all()
    )


@router.get("/{deal_id}", response_model=DealResponse)
def get_deal(
    deal_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve one deal by ID."""

    deal = db.get(Deal, deal_id)

    if deal is None:
        raise HTTPException(
            status_code=404,
            detail="Deal not found",
        )

    return deal


@router.patch("/{deal_id}", response_model=DealResponse)
def update_deal(
    deal_id: int,
    payload: DealUpdate,
    db: Session = Depends(get_db),
):
    """Update a deal, enforce active policies, and audit stage changes."""

    deal = db.get(Deal, deal_id)

    if deal is None:
        raise HTTPException(
            status_code=404,
            detail="Deal not found",
        )

    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=422,
            detail="Provide at least one field to update",
        )

    # Required fields cannot be explicitly set to null.
    for field in ("name", "stage", "probability"):
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null",
            )

    # Validate the final company/contact relationship.
    new_company_id = updates.get("company_id", deal.company_id)
    new_contact_id = updates.get("contact_id", deal.contact_id)

    validate_relationships(
        db,
        company_id=new_company_id,
        contact_id=new_contact_id,
    )

    previous_stage = deal.stage
    new_stage = updates.get("stage", previous_stage)

    # IMPORTANT:
    # Policy evaluation only happens when the stage actually changes.
    # This prevents unrelated updates from referencing undefined variables.
    if new_stage != previous_stage:
        applicable_policies, violations = evaluate_active_policies(
            db,
            deal,
            new_stage,
        )

        if applicable_policies:
            policy_snapshot = [
                {
                    "policy_id": policy.id,
                    "policy_key": policy.policy_key,
                    "version": policy.version,
                    "name": policy.name,
                }
                for policy in applicable_policies
            ]

            evaluation = PolicyEvaluation(
                deal_id=deal.id,
                from_stage=previous_stage,
                to_stage=new_stage,
                status="blocked" if violations else "allowed",
                policy_versions=policy_snapshot,
                violations=violations,
            )

            db.add(evaluation)

            if violations:
                # No deal fields have been changed yet.
                # Commit only the blocked-attempt audit record.
                try:
                    db.commit()
                except Exception:
                    db.rollback()
                    raise

                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": (
                            "Deal stage transition blocked by sales policies"
                        ),
                        "deal_id": deal.id,
                        "from_stage": previous_stage,
                        "to_stage": new_stage,
                        "violations": violations,
                    },
                )

    # Apply updates only after policy validation succeeds.
    for field, value in updates.items():
        setattr(deal, field, value)

    # Record history only when the stage genuinely changes.
    if new_stage != previous_stage:
        db.add(
            DealStageHistory(
                deal_id=deal.id,
                from_stage=previous_stage,
                to_stage=new_stage,
            )
        )

    try:
        # Allowed policy evaluations, deal updates, and stage history
        # are committed together.
        db.commit()
        db.refresh(deal)

    except Exception:
        db.rollback()
        raise

    # Critical: return the updated ORM object for DealResponse.
    return deal


@router.delete("/{deal_id}", status_code=204)
def delete_deal(
    deal_id: int,
    db: Session = Depends(get_db),
):
    """Delete a deal."""

    deal = db.get(Deal, deal_id)

    if deal is None:
        raise HTTPException(
            status_code=404,
            detail="Deal not found",
        )

    db.delete(deal)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return None


@router.post("/{deal_id}/transition", response_model=DealResponse)
def transition_deal(
    deal_id: int,
    payload: DealTransitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Transition a deal through the policy engine.

    A transition with violations is blocked unless an authorized
    manager/admin supplies a meaningful override reason.
    """
    deal = db.get(Deal, deal_id)

    if deal is None:
        raise HTTPException(
            status_code=404,
            detail="Deal not found",
        )

    previous_stage = deal.stage
    new_stage = payload.target_stage
    override_reason = payload.override_reason

    if previous_stage == new_stage:
        raise HTTPException(
            status_code=422,
            detail="The deal is already in the requested stage",
        )

    policies, violations = evaluate_active_policies(
        db,
        deal,
        new_stage,
    )

    if violations and override_reason is not None:
        if current_user.role not in {"admin", "manager"}:
            raise HTTPException(
                status_code=403,
                detail="Manager or admin permission required to override a policy",
            )

    policy_snapshot = [
        {
            "policy_id": policy.id,
            "policy_key": policy.policy_key,
            "version": policy.version,
            "name": policy.name,
        }
        for policy in policies
    ]

    evaluation = None

    if policies:
        if violations and override_reason is None:
            evaluation_status = "blocked"
        elif violations:
            evaluation_status = "overridden"
        else:
            evaluation_status = "allowed"

        evaluation = PolicyEvaluation(
            deal_id=deal.id,
            from_stage=previous_stage,
            to_stage=new_stage,
            status=evaluation_status,
            policy_versions=policy_snapshot,
            violations=violations,
            override_reason=(
                override_reason
                if evaluation_status == "overridden"
                else None
            ),
            evaluated_by=current_user.email,
        )

        db.add(evaluation)

    if violations and override_reason is None:
        # Persist the blocked attempt; do not change the deal.
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        raise HTTPException(
            status_code=409,
            detail={
                "message": "Deal transition blocked by sales policies",
                "deal_id": deal.id,
                "from_stage": previous_stage,
                "to_stage": new_stage,
                "violations": violations,
                "override_available_to": ["admin", "manager"],
            },
        )

    # Policies passed, or an authorized override has been supplied.
    deal.stage = new_stage

    db.add(
        DealStageHistory(
            deal_id=deal.id,
            from_stage=previous_stage,
            to_stage=new_stage,
        )
    )

    try:
        # Save the transition, stage history, and evaluation atomically.
        db.commit()
        db.refresh(deal)
    except Exception:
        db.rollback()
        raise

    return deal

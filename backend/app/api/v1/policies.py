
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Deal, PolicyEvaluation, SalesPolicyVersion
from app.schemas.policy import (
    PolicyCreate,
    PolicyEvaluationListResponse,
    PolicyListResponse,
    PolicyResponse,
    PolicySimulationResponse,
)
from app.services.policy_engine import evaluate_policy_for_deal
from app.api.dependencies import require_manager
from app.models import User

router = APIRouter(prefix="/policies", tags=["Sales Policies"])


@router.post("", response_model=PolicyResponse, status_code=201)
def create_policy_version(
    payload: PolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """
    Create a policy version in draft state.

    Posting the same policy_key creates the next version.
    Existing versions remain unchanged.
    """
    current_max = (
        db.query(func.max(SalesPolicyVersion.version))
        .filter(
            SalesPolicyVersion.policy_key == payload.policy_key
        )
        .scalar()
    )

    next_version = (current_max or 0) + 1

    policy = SalesPolicyVersion(
        **payload.model_dump(),
        version=next_version,
        is_active=False,
        created_by=current_user.email,
    )

    db.add(policy)

    try:
        db.commit()
        db.refresh(policy)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not create the policy version. Retry the request.",
        )
    except Exception:
        db.rollback()
        raise

    return policy


@router.get("", response_model=PolicyListResponse)
def list_policy_versions(
    db: Session = Depends(get_db),
    policy_key: str | None = None,
    active_only: bool = False,
    to_stage: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    filters = []

    if policy_key is not None:
        filters.append(SalesPolicyVersion.policy_key == policy_key)

    if active_only:
        filters.append(SalesPolicyVersion.is_active.is_(True))

    if to_stage is not None:
        filters.append(SalesPolicyVersion.to_stage == to_stage)

    query = db.query(SalesPolicyVersion).filter(*filters)
    total = query.count()

    items = (
        query.order_by(
            SalesPolicyVersion.policy_key.asc(),
            SalesPolicyVersion.version.desc(),
        )
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


# Keep this static route before /{policy_id}, to avoid path ambiguity.
@router.get(
    "/evaluations",
    response_model=PolicyEvaluationListResponse,
)
def list_policy_evaluations(
    db: Session = Depends(get_db),
    status: Literal["allowed", "blocked", "overridden"] | None = None,
    deal_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    filters = []

    if status is not None:
        filters.append(PolicyEvaluation.status == status)

    if deal_id is not None:
        filters.append(PolicyEvaluation.deal_id == deal_id)

    query = db.query(PolicyEvaluation).filter(*filters)
    total = query.count()

    items = (
        query.order_by(
            PolicyEvaluation.evaluated_at.desc(),
            PolicyEvaluation.id.desc(),
        )
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


@router.post(
    "/{policy_id}/activate",
    response_model=PolicyResponse,
)
def activate_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    policy = db.get(SalesPolicyVersion, policy_id)

    if policy is None:
        raise HTTPException(
            status_code=404,
            detail="Policy version not found",
        )

    # Lock versions with this key while switching the active version.
    versions = (
        db.query(SalesPolicyVersion)
        .filter(
            SalesPolicyVersion.policy_key == policy.policy_key
        )
        .with_for_update()
        .all()
    )

    for version in versions:
        version.is_active = version.id == policy.id

    try:
        db.commit()
        db.refresh(policy)
    except Exception:
        db.rollback()
        raise

    return policy


@router.post(
    "/{policy_id}/simulate",
    response_model=PolicySimulationResponse,
)
def simulate_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """
    Preview one policy against deals that could transition to its target stage.
    This operation does not activate the policy or change any deal.
    """
    policy = db.get(SalesPolicyVersion, policy_id)

    if policy is None:
        raise HTTPException(
            status_code=404,
            detail="Policy version not found",
        )

    query = db.query(Deal).filter(Deal.stage != policy.to_stage)

    if policy.from_stage is not None:
        query = query.filter(Deal.stage == policy.from_stage)

    deals = query.order_by(Deal.id.asc()).all()

    results = []

    for deal in deals:
        violations = evaluate_policy_for_deal(db, policy, deal)

        results.append(
            {
                "deal_id": deal.id,
                "deal_name": deal.name,
                "current_stage": deal.stage,
                "target_stage": policy.to_stage,
                "would_pass": len(violations) == 0,
                "violations": violations,
            }
        )

    passing_count = sum(
        1 for result in results if result["would_pass"]
    )

    return {
        "policy_id": policy.id,
        "policy_key": policy.policy_key,
        "policy_version": policy.version,
        "target_stage": policy.to_stage,
        "candidate_count": len(results),
        "passing_count": passing_count,
        "failing_count": len(results) - passing_count,
        "results": results,
    }


@router.get("/{policy_id}", response_model=PolicyResponse)
def get_policy_version(
    policy_id: int,
    db: Session = Depends(get_db),
):
    policy = db.get(SalesPolicyVersion, policy_id)

    if policy is None:
        raise HTTPException(
            status_code=404,
            detail="Policy version not found",
        )

    return policy


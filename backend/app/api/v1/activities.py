
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Activity
from app.schemas.activity import (
    ActivityCreate,
    ActivityListResponse,
    ActivityResponse,
    ActivityUpdate,
)
from app.api.v1.relationship_validation import validate_crm_links


router = APIRouter(prefix="/activities", tags=["Activities"])
DbSession = Depends(get_db)


@router.post("", response_model=ActivityResponse, status_code=201)
def create_activity(payload: ActivityCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_none=True)

    validate_crm_links(
        db,
        company_id=data.get("company_id"),
        contact_id=data.get("contact_id"),
        lead_id=data.get("lead_id"),
        deal_id=data.get("deal_id"),
    )

    activity = Activity(**data)
    db.add(activity)

    try:
        db.commit()
        db.refresh(activity)
    except Exception:
        db.rollback()
        raise

    return activity


@router.get("", response_model=ActivityListResponse)
def list_activities(
    db: Session = Depends(get_db),
    activity_type: str | None = None,
    company_id: int | None = Query(default=None, gt=0),
    contact_id: int | None = Query(default=None, gt=0),
    lead_id: int | None = Query(default=None, gt=0),
    deal_id: int | None = Query(default=None, gt=0),
    occurred_after: datetime | None = None,
    occurred_before: datetime | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    if occurred_after and occurred_before and occurred_after > occurred_before:
        raise HTTPException(
            status_code=422,
            detail="occurred_after must be before occurred_before",
        )

    filters = []

    if activity_type is not None:
        filters.append(Activity.activity_type == activity_type)
    if company_id is not None:
        filters.append(Activity.company_id == company_id)
    if contact_id is not None:
        filters.append(Activity.contact_id == contact_id)
    if lead_id is not None:
        filters.append(Activity.lead_id == lead_id)
    if deal_id is not None:
        filters.append(Activity.deal_id == deal_id)
    if occurred_after is not None:
        filters.append(Activity.occurred_at >= occurred_after)
    if occurred_before is not None:
        filters.append(Activity.occurred_at <= occurred_before)

    query = db.query(Activity).filter(*filters)
    total = db.query(func.count(Activity.id)).filter(*filters).scalar() or 0

    items = (
        query.order_by(Activity.occurred_at.desc(), Activity.id.desc())
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


@router.get("/{activity_id}", response_model=ActivityResponse)
def get_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = db.get(Activity, activity_id)

    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    return activity


@router.patch("/{activity_id}", response_model=ActivityResponse)
def update_activity(
    activity_id: int,
    payload: ActivityUpdate,
    db: Session = Depends(get_db),
):
    activity = db.get(Activity, activity_id)

    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=422,
            detail="Provide at least one field to update",
        )

    for field in ("activity_type", "subject", "occurred_at"):
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null",
            )

    link_fields = ("company_id", "contact_id", "lead_id", "deal_id")
    links = {
        field: updates.get(field, getattr(activity, field))
        for field in link_fields
    }

    validate_crm_links(db, **links)

    for field, value in updates.items():
        setattr(activity, field, value)

    try:
        db.commit()
        db.refresh(activity)
    except Exception:
        db.rollback()
        raise

    return activity


@router.delete("/{activity_id}", status_code=204)
def delete_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = db.get(Activity, activity_id)

    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    db.delete(activity)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return None

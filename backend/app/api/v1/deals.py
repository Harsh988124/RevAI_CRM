
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.crm import Company, Contact, Deal
from app.schemas.deal import (
    DealCreate,
    DealListResponse,
    DealResponse,
    DealStage,
    DealUpdate,
)

router = APIRouter(prefix="/deals", tags=["Deals"])

DbSession = Annotated[Session, Depends(get_db)]


def validate_relationships(
    db: Session,
    company_id: int | None,
    contact_id: int | None,
) -> None:
    contact = None

    if company_id is not None and db.get(Company, company_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    if contact_id is not None:
        contact = db.get(Contact, contact_id)
        if contact is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found",
            )

    if (
        company_id is not None
        and contact is not None
        and contact.company_id is not None
        and contact.company_id != company_id
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The selected contact does not belong to the selected company",
        )


@router.post(
    "",
    response_model=DealResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_deal(payload: DealCreate, db: DbSession):
    validate_relationships(db, payload.company_id, payload.contact_id)

    deal = Deal(**payload.model_dump(mode="json"))

    try:
        db.add(deal)
        db.commit()
        db.refresh(deal)
    except Exception:
        db.rollback()
        raise

    return deal


@router.get("", response_model=DealListResponse)
def list_deals(
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    stage_filter: DealStage | None = Query(default=None, alias="stage"),
    company_id: int | None = Query(default=None, gt=0),
    min_amount: float | None = Query(default=None, ge=0),
    max_amount: float | None = Query(default=None, ge=0),
):
    if (
        min_amount is not None
        and max_amount is not None
        and min_amount > max_amount
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_amount cannot exceed max_amount",
        )

    statement = select(Deal)

    if stage_filter is not None:
        statement = statement.where(Deal.stage == stage_filter)

    if company_id is not None:
        statement = statement.where(Deal.company_id == company_id)

    if min_amount is not None:
        statement = statement.where(Deal.amount >= min_amount)

    if max_amount is not None:
        statement = statement.where(Deal.amount <= max_amount)

    total = db.scalar(
        select(func.count()).select_from(statement.subquery())
    ) or 0

    deals = db.scalars(
        statement.order_by(Deal.id.desc()).limit(limit).offset(offset)
    ).all()

    return {
        "items": deals,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{deal_id}", response_model=DealResponse)
def get_deal(deal_id: int, db: DbSession):
    deal = db.get(Deal, deal_id)

    if deal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found",
        )

    return deal


@router.patch("/{deal_id}", response_model=DealResponse)
def update_deal(
    deal_id: int,
    payload: DealUpdate,
    db: DbSession,
):
    deal = db.get(Deal, deal_id)

    if deal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found",
        )

    updates = payload.model_dump(exclude_unset=True, mode="json")

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one field to update",
        )

    if "name" in updates and updates["name"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Deal name cannot be null",
        )

    company_id = updates.get("company_id", deal.company_id)
    contact_id = updates.get("contact_id", deal.contact_id)

    validate_relationships(db, company_id, contact_id)

    for field, value in updates.items():
        setattr(deal, field, value)

    try:
        db.commit()
        db.refresh(deal)
    except Exception:
        db.rollback()
        raise

    return deal


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deal(deal_id: int, db: DbSession):
    deal = db.get(Deal, deal_id)

    if deal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found",
        )

    try:
        db.delete(deal)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return Response(status_code=status.HTTP_204_NO_CONTENT)

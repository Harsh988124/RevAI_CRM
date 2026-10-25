
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.crm import Company, Contact, Lead
from app.schemas.lead import (
    LeadCreate,
    LeadListResponse,
    LeadResponse,
    LeadStatus,
    LeadUpdate,
)

router = APIRouter(prefix="/leads", tags=["Leads"])

DbSession = Annotated[Session, Depends(get_db)]


def validate_relationships(
    db: Session,
    company_id: int | None,
    contact_id: int | None,
) -> None:
    company = None
    contact = None

    if company_id is not None:
        company = db.get(Company, company_id)
        if company is None:
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

    # A lead's selected company and contact must be consistent.
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
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_lead(payload: LeadCreate, db: DbSession):
    validate_relationships(db, payload.company_id, payload.contact_id)

    lead = Lead(**payload.model_dump(mode="json"))

    try:
        db.add(lead)
        db.commit()
        db.refresh(lead)
    except Exception:
        db.rollback()
        raise

    return lead


@router.get("", response_model=LeadListResponse)
def list_leads(
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: LeadStatus | None = Query(default=None, alias="status"),
    company_id: int | None = Query(default=None, gt=0),
):
    statement = select(Lead)

    if status_filter is not None:
        statement = statement.where(Lead.status == status_filter)

    if company_id is not None:
        statement = statement.where(Lead.company_id == company_id)

    total_statement = select(func.count()).select_from(statement.subquery())
    total = db.scalar(total_statement) or 0

    leads = db.scalars(
        statement.order_by(Lead.id.desc()).limit(limit).offset(offset)
    ).all()

    return {
        "items": leads,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: int, db: DbSession):
    lead = db.get(Lead, lead_id)

    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    return lead


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int,
    payload: LeadUpdate,
    db: DbSession,
):
    lead = db.get(Lead, lead_id)

    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    updates = payload.model_dump(exclude_unset=True, mode="json")

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one field to update",
        )

    if "first_name" in updates and updates["first_name"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="First name cannot be null",
        )

    if "last_name" in updates and updates["last_name"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Last name cannot be null",
        )

    # Validate relationships using existing values for fields not supplied.
    company_id = updates.get("company_id", lead.company_id)
    contact_id = updates.get("contact_id", lead.contact_id)

    validate_relationships(db, company_id, contact_id)

    for field, value in updates.items():
        setattr(lead, field, value)

    try:
        db.commit()
        db.refresh(lead)
    except Exception:
        db.rollback()
        raise

    return lead


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(lead_id: int, db: DbSession):
    lead = db.get(Lead, lead_id)

    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    try:
        db.delete(lead)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return Response(status_code=status.HTTP_204_NO_CONTENT)

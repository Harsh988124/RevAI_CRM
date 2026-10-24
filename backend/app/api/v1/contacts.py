
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.crm import Company, Contact
from app.schemas.contact import (
    ContactCreate,
    ContactListResponse,
    ContactResponse,
    ContactUpdate,
)

router = APIRouter(prefix="/contacts", tags=["Contacts"])

DbSession = Annotated[Session, Depends(get_db)]


def validate_company(db: Session, company_id: int | None) -> None:
    if company_id is not None and db.get(Company, company_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )


@router.post(
    "",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_contact(payload: ContactCreate, db: DbSession):
    validate_company(db, payload.company_id)

    contact = Contact(**payload.model_dump(mode="json"))

    try:
        db.add(contact)
        db.commit()
        db.refresh(contact)
    except Exception:
        db.rollback()
        raise

    return contact


@router.get("", response_model=ContactListResponse)
def list_contacts(
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    total = db.scalar(select(func.count()).select_from(Contact)) or 0

    statement = (
        select(Contact)
        .order_by(Contact.id.desc())
        .limit(limit)
        .offset(offset)
    )
    contacts = db.scalars(statement).all()

    return {
        "items": contacts,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(contact_id: int, db: DbSession):
    contact = db.get(Contact, contact_id)

    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    return contact


@router.patch("/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: int,
    payload: ContactUpdate,
    db: DbSession,
):
    contact = db.get(Contact, contact_id)

    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    updates = payload.model_dump(exclude_unset=True, mode="json")

    if "company_id" in updates:
        validate_company(db, updates["company_id"])

    for field, value in updates.items():
        setattr(contact, field, value)

    try:
        db.commit()
        db.refresh(contact)
    except Exception:
        db.rollback()
        raise

    return contact


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_contact(contact_id: int, db: DbSession):
    contact = db.get(Contact, contact_id)

    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found",
        )

    try:
        db.delete(contact)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return Response(status_code=status.HTTP_204_NO_CONTENT)

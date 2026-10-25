from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.crm import Company
from app.schemas.company import (
    CompanyResponse,
    CompanyListResponse,
    CompanyCreate,
    CompanyUpdate,
)

router = APIRouter(prefix="/companies",tags=["Companies"])

DbSession = Annotated[Session,Depends(get_db)]

@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
)

def create_company(payload:CompanyCreate, db: DbSession):
    company = Company(**payload.model_dump(mode="json"))

    try:
        db.add(company)
        db.commit()
        db.refresh(company)
    except Exception:
        db.rollback()
        raise

    return company

@router.get("", response_model=CompanyListResponse)
def list_companies(
    db: DbSession,
    limit: int = Query(default=20,ge=1,le=100),
    offset: int =Query(default=0,ge=0),
):
    total = db.scalar(select(func.count()).select_from(Company)) or 0

    statement = (
        select(Company)
        .order_by(Company.id.desc())
        .limit(limit)
        .offset(offset)
    )
    companies = db.scalars(statement).all()

    return {
        "items": companies,
        "total": total,
        "limit": limit,
        "offset": offset,
    }

@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(company_id: int , db : DbSession):
    company = db.get(Company, company_id)

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    return company


@router.patch("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: int,
    payload: CompanyUpdate,
    db: DbSession,
):
    company = db.get(Company, company_id)

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    updates = payload.model_dump(exclude_unset=True, mode="json")

    # Reject an empty PATCH request.
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one field to update",
        )

    # The company name is required.
    if "name" in updates and updates["name"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Company name cannot be null",
        )

    for field, value in updates.items():
        setattr(company, field, value)

    try:
        db.commit()
        db.refresh(company)
    except Exception:
        db.rollback()
        raise

    return company


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_company(company_id: int, db: DbSession):
    company = db.get(Company, company_id)

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    try:
        db.delete(company)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return Response(status_code=status.HTTP_204_NO_CONTENT)

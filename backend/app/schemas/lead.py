
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


LeadStatus = Literal[
    "new",
    "contacted",
    "qualified",
    "unqualified",
    "converted",
]


class LeadBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    status: LeadStatus = "new"
    source: str | None = Field(default=None, max_length=100)
    estimated_value: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=15,
        decimal_places=2,
    )
    company_id: int | None = Field(default=None, gt=0)
    contact_id: int | None = Field(default=None, gt=0)


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    status: LeadStatus | None = None
    source: str | None = Field(default=None, max_length=100)
    estimated_value: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=15,
        decimal_places=2,
    )
    company_id: int | None = Field(default=None, gt=0)
    contact_id: int | None = Field(default=None, gt=0)


class LeadResponse(LeadBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int
    limit: int
    offset: int

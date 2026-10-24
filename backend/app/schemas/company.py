
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class CompanyBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    industry: str | None = Field(default=None, max_length=100)
    website: HttpUrl | None = None
    phone: str | None = Field(default=None, max_length=30)
    employee_count: int | None = Field(default=None, ge=0)
    annual_revenue: Decimal | None = Field(default=None, ge=0)
    description: str | None = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    industry: str | None = Field(default=None, max_length=100)
    website: HttpUrl | None = None
    phone: str | None = Field(default=None, max_length=30)
    employee_count: int | None = Field(default=None, ge=0)
    annual_revenue: Decimal | None = Field(default=None, ge=0)
    description: str | None = None


class CompanyResponse(CompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyListResponse(BaseModel):
    items: list[CompanyResponse]
    total: int
    limit: int
    offset: int

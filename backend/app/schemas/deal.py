
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


DealStage = Literal[
    "qualification",
    "discovery",
    "proposal",
    "negotiation",
    "closed_won",
    "closed_lost",
]


class DealBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    amount: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=15,
        decimal_places=2,
    )
    stage: DealStage = "qualification"
    probability: int = Field(default=10, ge=0, le=100)
    expected_close_date: date | None = None
    description: str | None = None
    company_id: int | None = Field(default=None, gt=0)
    contact_id: int | None = Field(default=None, gt=0)


class DealCreate(DealBase):
    pass


class DealUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    amount: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=15,
        decimal_places=2,
    )
    stage: DealStage | None = None
    probability: int | None = Field(default=None, ge=0, le=100)
    expected_close_date: date | None = None
    description: str | None = None
    company_id: int | None = Field(default=None, gt=0)
    contact_id: int | None = Field(default=None, gt=0)


class DealResponse(DealBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DealListResponse(BaseModel):
    items: list[DealResponse]
    total: int
    limit: int
    offset: int


from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ActivityType = Literal["call", "email", "meeting", "note"]


class ActivityCreate(BaseModel):
    activity_type: ActivityType
    subject: str = Field(min_length=1, max_length=200)
    description: str | None = None
    outcome: str | None = Field(default=None, max_length=100)
    duration_minutes: int | None = Field(default=None, ge=0, le=1440)
    occurred_at: datetime | None = None

    company_id: int | None = Field(default=None, gt=0)
    contact_id: int | None = Field(default=None, gt=0)
    lead_id: int | None = Field(default=None, gt=0)
    deal_id: int | None = Field(default=None, gt=0)


class ActivityUpdate(BaseModel):
    activity_type: ActivityType | None = None
    subject: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    outcome: str | None = Field(default=None, max_length=100)
    duration_minutes: int | None = Field(default=None, ge=0, le=1440)
    occurred_at: datetime | None = None

    company_id: int | None = Field(default=None, gt=0)
    contact_id: int | None = Field(default=None, gt=0)
    lead_id: int | None = Field(default=None, gt=0)
    deal_id: int | None = Field(default=None, gt=0)


class ActivityResponse(BaseModel):
    id: int
    activity_type: ActivityType
    subject: str
    description: str | None
    outcome: str | None
    duration_minutes: int | None
    occurred_at: datetime

    company_id: int | None
    contact_id: int | None
    lead_id: int | None
    deal_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityListResponse(BaseModel):
    items: list[ActivityResponse]
    total: int
    limit: int
    offset: int

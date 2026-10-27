
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TaskStatus = Literal["todo", "in_progress", "completed", "cancelled"]
TaskPriority = Literal["low", "medium", "high", "urgent"]


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None

    status: TaskStatus = "todo"
    priority: TaskPriority = "medium"

    due_at: datetime | None = None
    assigned_to: str | None = Field(default=None, max_length=120)

    company_id: int | None = Field(default=None, gt=0)
    contact_id: int | None = Field(default=None, gt=0)
    lead_id: int | None = Field(default=None, gt=0)
    deal_id: int | None = Field(default=None, gt=0)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None

    status: TaskStatus | None = None
    priority: TaskPriority | None = None

    due_at: datetime | None = None
    assigned_to: str | None = Field(default=None, max_length=120)

    company_id: int | None = Field(default=None, gt=0)
    contact_id: int | None = Field(default=None, gt=0)
    lead_id: int | None = Field(default=None, gt=0)
    deal_id: int | None = Field(default=None, gt=0)


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_at: datetime | None
    completed_at: datetime | None
    assigned_to: str | None

    company_id: int | None
    contact_id: int | None
    lead_id: int | None
    deal_id: int | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    limit: int
    offset: int

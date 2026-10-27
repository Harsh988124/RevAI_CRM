
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.relationship_validation import validate_crm_links
from app.db.session import get_db
from app.models import Task
from app.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)


router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()

    validate_crm_links(
        db,
        company_id=data.get("company_id"),
        contact_id=data.get("contact_id"),
        lead_id=data.get("lead_id"),
        deal_id=data.get("deal_id"),
    )

    if data["status"] == "completed":
        data["completed_at"] = datetime.now(timezone.utc)

    task = Task(**data)
    db.add(task)

    try:
        db.commit()
        db.refresh(task)
    except Exception:
        db.rollback()
        raise

    return task


@router.get("", response_model=TaskListResponse)
def list_tasks(
    db: Session = Depends(get_db),
    status: Literal[
        "todo", "in_progress", "completed", "cancelled"
    ] | None = None,
    priority: Literal["low", "medium", "high", "urgent"] | None = None,
    company_id: int | None = Query(default=None, gt=0),
    contact_id: int | None = Query(default=None, gt=0),
    lead_id: int | None = Query(default=None, gt=0),
    deal_id: int | None = Query(default=None, gt=0),
    assigned_to: str | None = None,
    due_before: datetime | None = None,
    due_after: datetime | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    if due_after and due_before and due_after > due_before:
        raise HTTPException(
            status_code=422,
            detail="due_after must be before due_before",
        )

    filters = []

    if status is not None:
        filters.append(Task.status == status)
    if priority is not None:
        filters.append(Task.priority == priority)
    if company_id is not None:
        filters.append(Task.company_id == company_id)
    if contact_id is not None:
        filters.append(Task.contact_id == contact_id)
    if lead_id is not None:
        filters.append(Task.lead_id == lead_id)
    if deal_id is not None:
        filters.append(Task.deal_id == deal_id)
    if assigned_to is not None:
        filters.append(Task.assigned_to == assigned_to)
    if due_before is not None:
        filters.append(Task.due_at <= due_before)
    if due_after is not None:
        filters.append(Task.due_at >= due_after)

    query = db.query(Task).filter(*filters)
    total = db.query(func.count(Task.id)).filter(*filters).scalar() or 0

    items = (
        query.order_by(Task.due_at.asc().nulls_last(), Task.id.desc())
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


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=422,
            detail="Provide at least one field to update",
        )

    for field in ("title", "status", "priority"):
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null",
            )

    link_fields = ("company_id", "contact_id", "lead_id", "deal_id")
    links = {
        field: updates.get(field, getattr(task, field))
        for field in link_fields
    }

    validate_crm_links(db, **links)

    new_status = updates.get("status", task.status)

    if new_status == "completed":
        if task.status != "completed" or task.completed_at is None:
            task.completed_at = datetime.now(timezone.utc)
    elif "status" in updates:
        task.completed_at = None

    for field, value in updates.items():
        setattr(task, field, value)

    try:
        db.commit()
        db.refresh(task)
    except Exception:
        db.rollback()
        raise

    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return None


from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import RevenueFinding
from app.schemas.finding import (
    FindingDismissRequest,
    FindingSummaryResponse,
    IntelligenceRunResponse,
    RevenueFindingListResponse,
    RevenueFindingResponse,
)
from app.services.revenue_intelligence import scan_revenue_intelligence


router = APIRouter(
    prefix="/intelligence",
    tags=["Revenue Intelligence"],
)


@router.post("/run", response_model=IntelligenceRunResponse)
def run_intelligence_scan(
    stalled_days: int = Query(default=14, ge=1, le=365),
    inactive_days: int = Query(default=14, ge=1, le=365),
    lead_followup_days: int = Query(default=3, ge=1, le=90),
    next_step_days: int = Query(default=3, ge=1, le=90),
    db: Session = Depends(get_db),
):
    return scan_revenue_intelligence(
        db,
        stalled_days=stalled_days,
        inactive_days=inactive_days,
        lead_followup_days=lead_followup_days,
        next_step_days=next_step_days,
    )


@router.get("/findings", response_model=RevenueFindingListResponse)
def list_findings(
    db: Session = Depends(get_db),
    status: Literal["open", "resolved", "dismissed"] | None = "open",
    severity: Literal["low", "medium", "high", "critical"] | None = None,
    rule_code: str | None = Query(default=None, max_length=60),
    entity_type: str | None = Query(default=None, max_length=30),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    filters = []

    if status is not None:
        filters.append(RevenueFinding.status == status)

    if severity is not None:
        filters.append(RevenueFinding.severity == severity)

    if rule_code is not None:
        filters.append(RevenueFinding.rule_code == rule_code)

    if entity_type is not None:
        filters.append(RevenueFinding.entity_type == entity_type)

    query = db.query(RevenueFinding).filter(*filters)

    total = query.count()

    items = (
        query.order_by(
            RevenueFinding.last_detected_at.desc(),
            RevenueFinding.id.desc(),
        )
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


@router.get("/summary", response_model=FindingSummaryResponse)
def get_intelligence_summary(db: Session = Depends(get_db)):
    open_findings = (
        db.query(RevenueFinding)
        .filter(RevenueFinding.status == "open")
        .all()
    )

    severity_counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }
    rule_counts: dict[str, int] = {}

    for finding in open_findings:
        severity_counts[finding.severity] += 1
        rule_counts[finding.rule_code] = (
            rule_counts.get(finding.rule_code, 0) + 1
        )

    return {
        "open_findings": len(open_findings),
        "by_severity": severity_counts,
        "by_rule": rule_counts,
    }


@router.get(
    "/findings/{finding_id}",
    response_model=RevenueFindingResponse,
)
def get_finding(
    finding_id: int,
    db: Session = Depends(get_db),
):
    finding = db.get(RevenueFinding, finding_id)

    if finding is None:
        raise HTTPException(
            status_code=404,
            detail="Revenue finding not found",
        )

    return finding


@router.post(
    "/findings/{finding_id}/dismiss",
    response_model=RevenueFindingResponse,
)
def dismiss_finding(
    finding_id: int,
    payload: FindingDismissRequest,
    db: Session = Depends(get_db),
):
    finding = db.get(RevenueFinding, finding_id)

    if finding is None:
        raise HTTPException(
            status_code=404,
            detail="Revenue finding not found",
        )

    if finding.status == "dismissed":
        raise HTTPException(
            status_code=409,
            detail="Finding has already been dismissed",
        )

    finding.status = "dismissed"
    finding.resolved_at = datetime.now(timezone.utc)
    finding.disposition_reason = payload.reason.strip()

    if len(finding.disposition_reason) < 3:
        raise HTTPException(
            status_code=422,
            detail="Dismissal reason must contain at least 3 non-space characters",
        )

    try:
        db.commit()
        db.refresh(finding)
    except Exception:
        db.rollback()
        raise

    return finding

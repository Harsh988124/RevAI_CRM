
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


FindingStatus = Literal["open", "resolved", "dismissed"]
FindingSeverity = Literal["low", "medium", "high", "critical"]


class RevenueFindingResponse(BaseModel):
    id: int
    fingerprint: str
    rule_code: str
    title: str
    description: str
    recommendation: str
    severity: FindingSeverity
    status: FindingStatus
    entity_type: str
    entity_id: int
    evidence: dict[str, Any]
    first_detected_at: datetime
    last_detected_at: datetime
    resolved_at: datetime | None
    disposition_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RevenueFindingListResponse(BaseModel):
    items: list[RevenueFindingResponse]
    total: int
    limit: int
    offset: int


class FindingDismissRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class IntelligenceRunResponse(BaseModel):
    scanned_at: datetime
    findings_created: int
    findings_updated: int
    findings_resolved: int
    open_findings: int
    entities_scanned: dict[str, int]


class FindingSummaryResponse(BaseModel):
    open_findings: int
    by_severity: dict[str, int]
    by_rule: dict[str, int]

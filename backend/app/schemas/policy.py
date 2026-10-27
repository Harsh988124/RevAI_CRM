
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


DealStage = Literal[
    "qualification",
    "discovery",
    "proposal",
    "negotiation",
    "closed_won",
    "closed_lost",
]

PolicyField = Literal[
    "amount",
    "expected_close_date",
    "company_id",
    "contact_id",
    "description",
]

FindingStatus = Literal["open", "blocked", "overridden"]


class PolicyCreate(BaseModel):
    policy_key: str = Field(
        min_length=3,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    name: str = Field(min_length=3, max_length=200)
    description: str | None = None

    from_stage: DealStage | None = None
    to_stage: DealStage

    required_fields: list[PolicyField] = Field(
        default_factory=list,
        max_length=5,
    )

    min_amount: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=15,
        decimal_places=2,
    )

    min_probability: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    require_open_task: bool = False

    @field_validator("required_fields")
    @classmethod
    def unique_required_fields(
        cls,
        fields: list[PolicyField],
    ) -> list[PolicyField]:
        if len(fields) != len(set(fields)):
            raise ValueError(
                "required_fields must not contain duplicates"
            )
        return fields


class PolicyResponse(BaseModel):
    id: int
    policy_key: str
    version: int
    name: str
    description: str | None
    from_stage: DealStage | None
    to_stage: DealStage
    required_fields: list[PolicyField]
    min_amount: Decimal | None
    min_probability: int | None
    require_open_task: bool
    is_active: bool
    created_by: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PolicyListResponse(BaseModel):
    items: list[PolicyResponse]
    total: int
    limit: int
    offset: int


class PolicyViolationResponse(BaseModel):
    policy_id: int
    policy_key: str
    policy_version: int
    code: str
    field: str | None
    message: str


class PolicyEvaluationResponse(BaseModel):
    id: int
    deal_id: int
    from_stage: DealStage | None
    to_stage: DealStage
    status: Literal["allowed", "blocked", "overridden"]
    policy_versions: list[dict[str, Any]]
    violations: list[PolicyViolationResponse]
    override_reason: str | None = None
    evaluated_by: str | None = None
    evaluated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PolicyEvaluationListResponse(BaseModel):
    items: list[PolicyEvaluationResponse]
    total: int
    limit: int
    offset: int


class PolicySimulationResult(BaseModel):
    deal_id: int
    deal_name: str
    current_stage: DealStage
    target_stage: DealStage
    would_pass: bool
    violations: list[PolicyViolationResponse]


class PolicySimulationResponse(BaseModel):
    policy_id: int
    policy_key: str
    policy_version: int
    target_stage: DealStage
    candidate_count: int
    passing_count: int
    failing_count: int
    results: list[PolicySimulationResult]

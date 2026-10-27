
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


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


class AIPolicyDraftRequest(BaseModel):
    instruction: str = Field(
        min_length=10,
        max_length=2000,
        description="Natural-language sales policy requested by a manager.",
    )


class GeneratedPolicySpec(BaseModel):
    name: str
    description: str
    from_stage: DealStage | None = None
    to_stage: DealStage
    required_fields: list[PolicyField] = Field(default_factory=list)
    min_amount: float | None = None
    min_probability: int | None = Field(default=None, ge=0, le=100)
    require_open_task: bool = False


class GeneratedPolicyAnalysis(BaseModel):
    implementable: bool
    policy: GeneratedPolicySpec | None = None
    clarification_questions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class AIPolicyDraft(BaseModel):
    policy_key: str
    name: str
    description: str
    from_stage: DealStage | None = None
    to_stage: DealStage
    required_fields: list[PolicyField] = Field(default_factory=list)
    min_amount: Decimal | None = None
    min_probability: int | None = Field(default=None, ge=0, le=100)
    require_open_task: bool = False

    model_config = ConfigDict(from_attributes=True)


class AIPolicyDraftResponse(BaseModel):
    model: str
    implementable: bool
    draft: AIPolicyDraft | None = None
    clarification_questions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

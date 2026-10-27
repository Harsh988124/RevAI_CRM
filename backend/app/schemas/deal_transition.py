
from typing import Literal

from pydantic import BaseModel, Field, field_validator


DealStage = Literal[
    "qualification",
    "discovery",
    "proposal",
    "negotiation",
    "closed_won",
    "closed_lost",
]


class DealTransitionRequest(BaseModel):
    target_stage: DealStage

    override_reason: str | None = Field(
        default=None,
        max_length=500,
    )

    @field_validator("override_reason")
    @classmethod
    def validate_override_reason(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if len(value) < 10:
            raise ValueError(
                "Override reason must contain at least 10 non-space characters"
            )

        return value

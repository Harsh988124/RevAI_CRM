
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


DealStage = Literal[
    "qualification",
    "discovery",
    "proposal",
    "negotiation",
    "closed_won",
    "closed_lost",
]


class DealStageHistoryResponse(BaseModel):
    id: int
    deal_id: int
    from_stage: DealStage | None
    to_stage: DealStage
    changed_at: datetime
    changed_by: str | None

    model_config = ConfigDict(from_attributes=True)

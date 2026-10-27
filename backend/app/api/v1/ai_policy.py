
from fastapi import APIRouter, Depends

from app.schemas.ai_policy import (
    AIPolicyDraftRequest,
    AIPolicyDraftResponse,
)
from app.services.ai_policy_drafting import draft_policy
from app.api.dependencies import require_manager
from app.models import User

router = APIRouter(
    prefix="/ai-policy",
    tags=["AI Policy Drafting"],
)


@router.post(
    "/draft",
    response_model=AIPolicyDraftResponse,
)
def generate_policy_draft(
    payload: AIPolicyDraftRequest,
    current_user: User = Depends(require_manager),
) -> AIPolicyDraftResponse:
    """
    Convert a manager's natural-language instruction into
    a structured sales-policy draft using NVIDIA AI.

    This endpoint does not save or activate the policy.
    """
    return draft_policy(payload.instruction)

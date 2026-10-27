
import json
import re
from decimal import Decimal

from fastapi import HTTPException
from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.ai_policy import (
    AIPolicyDraft,
    AIPolicyDraftResponse,
    GeneratedPolicyAnalysis,
)


SYSTEM_INSTRUCTIONS = """
You are RevPilot AI's sales-policy drafting assistant.

Convert the manager's instruction into a structured JSON policy draft.

Supported deal stages:
qualification, discovery, proposal, negotiation, closed_won, closed_lost.

Supported required fields:
amount, expected_close_date, company_id, contact_id, description.

Supported additional conditions:
min_amount, min_probability (0 to 100), require_open_task.

Return ONLY one valid JSON object with this shape:
{
  "implementable": true,
  "policy": {
    "name": "Policy name",
    "description": "Short explanation",
    "from_stage": "qualification",
    "to_stage": "proposal",
    "required_fields": ["contact_id", "expected_close_date"],
    "min_amount": 50000,
    "min_probability": 30,
    "require_open_task": true
  },
  "clarification_questions": [],
  "assumptions": []
}

Rules:
- Include every field shown in the JSON shape.
- Use null for unspecified optional values.
- If the request is ambiguous, set implementable to false,
  policy to null, and ask clarification questions.
- Do not invent requirements.
- Use only supported stages, fields, and conditions.
- Do not return SQL, Python code, or executable expressions.
- The result is a draft. Never claim it has been saved or activated.
"""


def make_policy_key(name: str) -> str:
    """Generate a stable, database-safe key from a policy name."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    slug = slug[:90].strip("_")

    if not slug:
        slug = "sales_policy"

    if not slug[0].isalpha():
        slug = f"policy_{slug}"

    return slug[:100]


def extract_json(content: str) -> dict:
    """Parse a JSON object, tolerating optional Markdown code fences."""
    text = content.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        # Some models may add a short prefix or suffix.
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end <= start:
            raise

        result = json.loads(text[start : end + 1])

    if not isinstance(result, dict):
        raise ValueError("The AI response must be a JSON object.")

    return result


def draft_policy(instruction: str) -> AIPolicyDraftResponse:
    if not settings.nvidia_api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "NVIDIA AI is not configured. "
                "Set NVIDIA_API_KEY in backend/.env and restart the API."
            ),
        )

    try:
        client = OpenAI(
            base_url=settings.nvidia_base_url,
            api_key=settings.nvidia_api_key,
            timeout=60.0,
            max_retries=1,
        )

        response = client.chat.completions.create(
            model=settings.nvidia_model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTIONS,
                },
                {
                    "role": "user",
                    "content": instruction,
                },
            ],
            temperature=0.1,
            max_tokens=1800,
            stream=False,
        )

        content = response.choices[0].message.content

        if not content or not content.strip():
            raise ValueError("The model returned an empty response.")

        parsed = extract_json(content)
        analysis = GeneratedPolicyAnalysis.model_validate(parsed)

    except HTTPException:
        raise
    except (OpenAIError, ValueError, ValidationError, IndexError, KeyError) as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "NVIDIA did not return a usable policy draft. "
                "Check the API key, model availability, and response format."
            ),
        ) from exc

    if not analysis.implementable or analysis.policy is None:
        return AIPolicyDraftResponse(
            model=settings.nvidia_model,
            implementable=False,
            draft=None,
            clarification_questions=analysis.clarification_questions,
            assumptions=analysis.assumptions,
        )

    spec = analysis.policy

    if spec.from_stage == spec.to_stage:
        return AIPolicyDraftResponse(
            model=settings.nvidia_model,
            implementable=False,
            draft=None,
            clarification_questions=[
                "The starting stage and target stage are identical. "
                "Please clarify the intended transition."
            ],
            assumptions=analysis.assumptions,
        )

    if spec.min_probability is not None and not (
        0 <= spec.min_probability <= 100
    ):
        return AIPolicyDraftResponse(
            model=settings.nvidia_model,
            implementable=False,
            draft=None,
            clarification_questions=[
                "Minimum probability must be between 0 and 100."
            ],
            assumptions=analysis.assumptions,
        )

    if spec.min_amount is not None and spec.min_amount < 0:
        return AIPolicyDraftResponse(
            model=settings.nvidia_model,
            implementable=False,
            draft=None,
            clarification_questions=[
                "Minimum deal amount cannot be negative."
            ],
            assumptions=analysis.assumptions,
        )

    draft = AIPolicyDraft(
        policy_key=make_policy_key(spec.name),
        name=spec.name,
        description=spec.description,
        from_stage=spec.from_stage,
        to_stage=spec.to_stage,
        required_fields=list(dict.fromkeys(spec.required_fields)),
        min_amount=(
            Decimal(str(spec.min_amount))
            if spec.min_amount is not None
            else None
        ),
        min_probability=spec.min_probability,
        require_open_task=spec.require_open_task,
    )

    return AIPolicyDraftResponse(
        model=settings.nvidia_model,
        implementable=True,
        draft=draft,
        clarification_questions=analysis.clarification_questions,
        assumptions=analysis.assumptions,
    )


import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.ai_policy import GeneratedPolicyAnalysis
import app.services.ai_policy_drafting as ai_service


class FakeCompletions:
    content = "{}"
    last_request = None

    def create(self, **kwargs):
        FakeCompletions.last_request = kwargs

        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=FakeCompletions.content
                    )
                )
            ]
        )


class FakeOpenAI:
    def __init__(self, **kwargs):
        self.chat = SimpleNamespace(
            completions=FakeCompletions()
        )


def set_fake_result(result):
    FakeCompletions.content = json.dumps(result)


def test_ai_policy_draft_returns_structured_policy(monkeypatch):
    monkeypatch.setattr(settings, "nvidia_api_key", "test-key")
    monkeypatch.setattr(
        settings,
        "nvidia_model",
        "nvidia/nemotron-3.5-lightning-30b-a3b",
    )
    monkeypatch.setattr(ai_service, "OpenAI", FakeOpenAI)

    set_fake_result(
        {
            "implementable": True,
            "policy": {
                "name": "Proposal Requirements",
                "description": "Required fields before Proposal",
                "from_stage": "qualification",
                "to_stage": "proposal",
                "required_fields": [
                    "contact_id",
                    "expected_close_date",
                ],
                "min_amount": 10000,
                "min_probability": 30,
                "require_open_task": True,
            },
            "clarification_questions": [],
            "assumptions": [],
        }
    )

    result = ai_service.draft_policy(
        "Require a contact, close date and open task before Proposal."
    )

    assert result.implementable is True
    assert result.draft is not None
    assert result.draft.policy_key == "proposal_requirements"
    assert result.draft.to_stage == "proposal"
    assert result.draft.require_open_task is True
    assert result.draft.min_probability == 30

    request = FakeCompletions.last_request
    assert request["model"] == "nvidia/nemotron-3.5-lightning-30b-a3b"


def test_ambiguous_instruction_requests_clarification(monkeypatch):
    monkeypatch.setattr(settings, "nvidia_api_key", "test-key")
    monkeypatch.setattr(ai_service, "OpenAI", FakeOpenAI)

    set_fake_result(
        {
            "implementable": False,
            "policy": None,
            "clarification_questions": [
                "Which deal stage should this policy apply to?"
            ],
            "assumptions": [],
        }
    )

    result = ai_service.draft_policy("Make the sales process stricter.")

    assert result.implementable is False
    assert result.draft is None
    assert len(result.clarification_questions) >= 1


def test_missing_nvidia_api_key_returns_503(monkeypatch):
    monkeypatch.setattr(settings, "nvidia_api_key", None)

    with pytest.raises(HTTPException) as error:
        ai_service.draft_policy(
            "Require a close date before Proposal."
        )

    assert error.value.status_code == 503


def test_invalid_json_returns_502(monkeypatch):
    monkeypatch.setattr(settings, "nvidia_api_key", "test-key")
    monkeypatch.setattr(ai_service, "OpenAI", FakeOpenAI)
    FakeCompletions.content = "This is not valid JSON."

    with pytest.raises(HTTPException) as error:
        ai_service.draft_policy(
            "Require a close date before Proposal."
        )

    assert error.value.status_code == 502

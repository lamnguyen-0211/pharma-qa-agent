"""Controlled, provider-neutral agent workflow.

The model provider is deliberately an interface. ChatGPT account sessions are not
supported server credentials for a general model API, so this service does not
pretend to implement an unofficial OAuth/token exchange.
"""

import re
from uuid import uuid4

from .models import ChatResponse, RiskLevel
from .store import AiStore

EMERGENCY = re.compile(r"chest pain|difficulty breathing|can't breathe|overdose|severe allergic", re.I)
HIGH_RISK = re.compile(r"dose|dosage|pregnan|side effect|contraindication|adverse", re.I)


class ModelProvider:
    """Future provider contract for a managed/local model runtime."""

    def complete(self, question: str) -> str:
        raise NotImplementedError


class PharmaAgent:
    """Single orchestrator with deterministic safety gates before model work."""

    def __init__(self, store: AiStore) -> None:
        self.store = store

    def classify(self, question: str) -> RiskLevel:
        if EMERGENCY.search(question):
            return "emergency"
        if HIGH_RISK.search(question):
            return "high"
        return "low"

    def answer(
        self,
        chat_session_id: str | None,
        business_session_id: str,
        question: str,
    ) -> ChatResponse:
        risk = self.classify(question)
        trace_id = str(uuid4())

        if risk == "emergency":
            response = ChatResponse(
                business_session_id=business_session_id,
                chat_session_id="",
                answer=("This may be an emergency. Contact local emergency services or a qualified "
                        "healthcare professional now. I cannot assess or treat an emergency."),
                risk_level=risk,
                trace_id=trace_id,
            )
        else:
            response = ChatResponse(
                business_session_id=business_session_id,
                chat_session_id="",
                answer=("The Python AI service is running, but no supported model provider is configured. "
                        "Connect an approved provider or local model runtime before enabling model responses. "
                        "For medical advice, consult a qualified healthcare professional."),
                risk_level=risk,
                trace_id=trace_id,
            )
        persisted_session_id = self.store.record_turn(
            chat_session_id,
            business_session_id,
            question,
            response,
        )
        return response.model_copy(update={"chat_session_id": persisted_session_id})

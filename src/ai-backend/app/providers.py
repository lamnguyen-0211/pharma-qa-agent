"""Provider-neutral boundaries used by the LangGraph workflow."""

from typing import Protocol

from .models import GeneratedAnswer, RetrievedChunk


class ChatProvider(Protocol):
    def generate(
        self,
        question: str,
        chunks: list[RetrievedChunk] | None,
    ) -> GeneratedAnswer:
        """Generate a general answer or one grounded in the supplied chunks."""


class KnowledgeRetriever(Protocol):
    def search(self, question: str) -> list[RetrievedChunk]:
        """Return approved, effective evidence for a question."""


class EmptyKnowledgeRetriever:
    def search(self, question: str) -> list[RetrievedChunk]:
        return []


class UnconfiguredChatProvider:
    def generate(
        self,
        question: str,
        chunks: list[RetrievedChunk] | None,
    ) -> GeneratedAnswer:
        return GeneratedAnswer(
            answer=(
                "The Python AI service is running, but no supported model provider is configured. "
                "Connect an approved provider or local model runtime before enabling model responses. "
                "For medical advice, consult a qualified healthcare professional."
            )
        )

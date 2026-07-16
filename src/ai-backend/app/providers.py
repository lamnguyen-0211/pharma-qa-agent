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


class EmbeddingProvider(Protocol):
    model_name: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed source chunks for indexing."""

    def embed_query(self, text: str) -> list[float]:
        """Embed one retrieval query."""


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


class SentenceTransformerEmbeddingProvider:
    """Lazy local embedding adapter for a configurable Hugging Face model."""

    QUERY_INSTRUCTION = (
        "Given a pharmaceutical information question, retrieve relevant approved "
        "document passages that answer the question."
    )

    def __init__(self, model_name: str, expected_dimension: int) -> None:
        self.model_name = model_name
        self.expected_dimension = expected_dimension
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    @staticmethod
    def _to_lists(vectors) -> list[list[float]]:
        return vectors.tolist() if hasattr(vectors, "tolist") else list(vectors)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self._load_model().encode(texts, normalize_embeddings=True)
        return self._to_lists(vectors)

    def embed_query(self, text: str) -> list[float]:
        query = f"Instruct: {self.QUERY_INSTRUCTION}\nQuery: {text}"
        return self.embed_documents([query])[0]

"""Environment-backed configuration for the AI service."""

import os
from dataclasses import dataclass


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _boolean(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    raise ValueError(f"{name} must be one of: 1, true, yes, or on")


@dataclass(frozen=True)
class Settings:
    ai_database_url: str
    gemini_api_key: str | None
    chat_model_name: str = "gemini-3.5-flash"
    embedding_type: str = "sentence-transformers"
    embedding_model_name: str = "Qwen/Qwen3-Embedding-0.6B"
    embedding_dimension: int = 1024
    rag_candidate_k: int = 15
    rag_rerank_enabled: bool = True
    reranker_model_name: str = "gemini-3.5-flash-lite"
    rag_top_k: int = 5
    rag_max_context_chars: int = 12_000
    knowledge_upload_max_bytes: int = 10_485_760

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            ai_database_url=os.environ["AI_DATABASE_URL"],
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            chat_model_name=os.getenv("CHAT_MODEL_NAME", "gemini-3.5-flash"),
            embedding_type=os.getenv("EMBEDDING_TYPE", "sentence-transformers"),
            embedding_model_name=os.getenv(
                "EMBEDDING_MODEL_NAME", "Qwen/Qwen3-Embedding-0.6B"
            ),
            embedding_dimension=_positive_int("EMBEDDING_DIMENSION", 1024),
            rag_candidate_k=_positive_int("RAG_CANDIDATE_K", 15),
            rag_rerank_enabled=_boolean("RAG_RERANK_ENABLED", True),
            reranker_model_name=os.getenv(
                "RERANKER_MODEL_NAME", "gemini-3.5-flash-lite"
            ),
            rag_top_k=_positive_int("RAG_TOP_K", 5),
            rag_max_context_chars=_positive_int("RAG_MAX_CONTEXT_CHARS", 12_000),
            knowledge_upload_max_bytes=_positive_int(
                "KNOWLEDGE_UPLOAD_MAX_BYTES", 10_485_760
            ),
        )

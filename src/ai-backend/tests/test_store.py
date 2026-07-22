import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.knowledge import EmbeddingConfigurationError
from app.models import RetrievedChunk
from app.providers import ModelProviderError
from app.store import PostgresAiStore, PostgresKnowledgeRetriever


class FakeCursor:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def execute(self, statement: str, **kwargs) -> None:
        self.statements.append(statement)


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self.fake_cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def cursor(self) -> FakeCursor:
        return self.fake_cursor


class FakeSearchStore:
    def __init__(self, chunks: list[RetrievedChunk] | None = None) -> None:
        self.chunks = chunks or []
        self.calls = []

    def search_knowledge(self, question, embedding, top_k):
        self.calls.append((question, embedding, top_k))
        return self.chunks


class FakeReranker:
    def __init__(self, result: list[RetrievedChunk] | None = None, error=None) -> None:
        self.result = result or []
        self.error = error
        self.calls = []

    def rerank(self, question, chunks, top_k):
        self.calls.append((question, chunks, top_k))
        if self.error is not None:
            raise self.error
        return self.result


class FakeQueryEmbedder:
    model_name = "fake-embedding"

    def __init__(self, vector: list[float]) -> None:
        self.vector = vector

    def embed_documents(self, texts):
        return [self.vector for _ in texts]

    def embed_query(self, text):
        return self.vector


def test_initialize_schema_applies_all_migrations_in_filename_order(monkeypatch):
    cursor = FakeCursor()
    fake_psycopg = SimpleNamespace(connect=lambda _: FakeConnection(cursor))
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)

    PostgresAiStore("postgresql://test").initialize_schema()

    assert len(cursor.statements) == 2
    assert cursor.statements[0].lstrip().startswith("CREATE TABLE IF NOT EXISTS chat_session")
    assert cursor.statements[1].lstrip().startswith("CREATE EXTENSION IF NOT EXISTS vector")


def test_knowledge_migration_defines_vector_and_hybrid_indexes():
    migration = (
        Path(__file__).parents[1] / "migrations" / "002_knowledge_base.sql"
    ).read_text(encoding="utf-8")

    assert "CREATE EXTENSION IF NOT EXISTS vector" in migration
    assert "embedding VECTOR(1024)" in migration
    assert "USING hnsw" in migration
    assert "USING gin" in migration


def test_retriever_rejects_query_dimension_before_database_search():
    store = FakeSearchStore()
    retriever = PostgresKnowledgeRetriever(
        store,
        FakeQueryEmbedder([0.1, 0.2]),
        expected_dimension=3,
        top_k=5,
        max_context_chars=12_000,
    )

    with pytest.raises(EmbeddingConfigurationError, match="dimension"):
        retriever.search("Product A")

    assert store.calls == []


def test_retriever_caps_total_context_without_reordering():
    chunks = [
        RetrievedChunk(
            chunk_id=f"chunk-{index}",
            document_id="document-1",
            title="Approved Label",
            version="3.2",
            content="x" * 10,
            score=1.0 - index / 10,
        )
        for index in range(3)
    ]
    retriever = PostgresKnowledgeRetriever(
        FakeSearchStore(chunks),
        FakeQueryEmbedder([0.1, 0.2, 0.3]),
        expected_dimension=3,
        top_k=5,
        max_context_chars=20,
    )

    result = retriever.search("Product A")

    assert [chunk.chunk_id for chunk in result] == ["chunk-0", "chunk-1"]


def test_retriever_requests_candidate_pool_and_returns_reranked_top_k():
    chunks = [
        RetrievedChunk(
            chunk_id=f"chunk-{index}",
            document_id="document-1",
            title="Approved Label",
            version="3.2",
            content=f"content-{index}",
            score=1.0 - index / 10,
        )
        for index in range(3)
    ]
    store = FakeSearchStore(chunks)
    reranker = FakeReranker([chunks[2], chunks[0], chunks[1]])
    retriever = PostgresKnowledgeRetriever(
        store,
        FakeQueryEmbedder([0.1, 0.2, 0.3]),
        expected_dimension=3,
        top_k=2,
        max_context_chars=12_000,
        candidate_k=15,
        reranker=reranker,
    )

    result = retriever.search("Product A")

    assert store.calls == [("Product A", [0.1, 0.2, 0.3], 15)]
    assert reranker.calls == [("Product A", chunks, 2)]
    assert [chunk.chunk_id for chunk in result] == ["chunk-2", "chunk-0"]


def test_retriever_falls_back_to_hybrid_order_when_reranker_fails():
    chunks = [
        RetrievedChunk(
            chunk_id=f"chunk-{index}",
            document_id="document-1",
            title="Approved Label",
            version="3.2",
            content=f"content-{index}",
            score=1.0 - index / 10,
        )
        for index in range(2)
    ]
    store = FakeSearchStore(chunks)
    reranker = FakeReranker(error=ModelProviderError("Reranking failed."))
    retriever = PostgresKnowledgeRetriever(
        store,
        FakeQueryEmbedder([0.1, 0.2, 0.3]),
        expected_dimension=3,
        top_k=2,
        max_context_chars=12_000,
        reranker=reranker,
    )

    result = retriever.search("Product A")

    assert [chunk.chunk_id for chunk in result] == ["chunk-0", "chunk-1"]


def test_retriever_skips_reranker_for_empty_candidates():
    reranker = FakeReranker()
    retriever = PostgresKnowledgeRetriever(
        FakeSearchStore(),
        FakeQueryEmbedder([0.1, 0.2, 0.3]),
        expected_dimension=3,
        top_k=2,
        max_context_chars=12_000,
        reranker=reranker,
    )

    assert retriever.search("Product A") == []
    assert reranker.calls == []

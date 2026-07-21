import os
from datetime import date, timedelta

import pytest

from app.knowledge import DocumentMetadata, prepare_document
from app.store import DuplicateDocumentError, PostgresAiStore, PostgresKnowledgeRetriever

pytestmark = pytest.mark.skipif(
    not os.getenv("AI_TEST_DATABASE_URL"),
    reason="AI_TEST_DATABASE_URL is required for pgvector integration tests",
)


class KeywordEmbedder:
    model_name = "integration-embedding"

    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text):
        vector = [0.0] * 1024
        vector[0] = 1.0 if "Product A" in text else 0.1
        vector[1] = 1.0 if "indication" in text.lower() else 0.1
        return vector


def metadata(title: str, status: str = "APPROVED", **updates) -> DocumentMetadata:
    values = {
        "title": title,
        "document_type": "PRODUCT_LABEL",
        "product": "Product A",
        "language": "en",
        "effective_date": date.today(),
        "expiration_date": date.today() + timedelta(days=365),
        "version": "1.0",
        "approval_status": status,
        "access_classification": "INTERNAL",
    }
    values.update(updates)
    return DocumentMetadata(**values)


@pytest.fixture
def store():
    postgres_store = PostgresAiStore(os.environ["AI_TEST_DATABASE_URL"])
    postgres_store.initialize_schema()
    postgres_store.clear_knowledge_for_tests()
    yield postgres_store
    postgres_store.clear_knowledge_for_tests()


def save(
    store,
    filename: str,
    document_metadata: DocumentMetadata,
    source: bytes | None = None,
):
    prepared = prepare_document(
        source or b"Product A approved indication and usage information.",
        filename,
        document_metadata,
    )
    embedder = KeywordEmbedder()
    return store.save_document(
        prepared,
        embedder.embed_documents([chunk.content for chunk in prepared.chunks]),
        embedder.model_name,
        1024,
    )


def test_hybrid_search_returns_only_approved_current_documents(store):
    approved = save(store, "approved.txt", metadata("Approved Label"))
    save(
        store,
        "draft.txt",
        metadata("Draft Label", status="DRAFT"),
        b"Draft Product A indication content must not be retrieved.",
    )
    save(
        store,
        "expired.txt",
        metadata(
            "Expired Label",
            effective_date=date.today() - timedelta(days=365),
            expiration_date=date.today() - timedelta(days=1),
        ),
        b"Expired Product A indication content must not be retrieved.",
    )

    results = PostgresKnowledgeRetriever(
        store,
        KeywordEmbedder(),
        expected_dimension=1024,
        top_k=5,
        max_context_chars=12_000,
    ).search("What is the Product A indication?")

    assert {chunk.document_id for chunk in results} == {approved.document_id}
    assert results[0].title == "Approved Label"


def test_duplicate_checksum_is_rejected_without_partial_document(store):
    save(store, "approved.txt", metadata("Approved Label"))

    with pytest.raises(DuplicateDocumentError):
        save(store, "duplicate.txt", metadata("Duplicate Label"))

    assert len(store.list_documents()) == 1

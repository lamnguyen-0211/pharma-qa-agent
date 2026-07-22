import hashlib
from datetime import date
from io import BytesIO

import pytest
from pydantic import ValidationError
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.config import Settings
from app.knowledge import (
    DocumentMetadata,
    EmbeddingConfigurationError,
    KnowledgeIngestionService,
    KnowledgeValidationError,
    prepare_document,
)


def metadata(**updates) -> DocumentMetadata:
    values = {
        "title": "Approved Label",
        "document_type": "PRODUCT_LABEL",
        "product": "Product A",
        "active_ingredient": "Ingredient A",
        "market": "Thailand",
        "jurisdiction": "TH",
        "language": "en",
        "effective_date": date(2026, 1, 1),
        "expiration_date": date(2027, 1, 1),
        "version": "3.2",
        "approval_status": "APPROVED",
        "audience": "INTERNAL",
        "access_classification": "INTERNAL",
    }
    values.update(updates)
    return DocumentMetadata(**values)


class RecordingDocumentStore:
    def __init__(self) -> None:
        self.saved = []

    def save_document(self, prepared, embeddings, model_name, dimension):
        self.saved.append((prepared, embeddings, model_name, dimension))
        return "document-1"


class FakeEmbedder:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.model_name = "fake-embedding"
        self.vectors = vectors
        self.document_calls: list[list[str]] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_calls.append(texts)
        return self.vectors

    def embed_query(self, text: str) -> list[float]:
        return self.vectors[0]


def test_settings_use_configurable_qwen_defaults(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AI_DATABASE_URL", "postgresql://test")
    monkeypatch.delenv("EMBEDDING_MODEL_NAME", raising=False)
    monkeypatch.delenv("EMBEDDING_DIMENSION", raising=False)

    settings = Settings.from_env()

    assert settings.embedding_model_name == "Qwen/Qwen3-Embedding-0.6B"
    assert settings.embedding_dimension == 1024
    assert settings.chat_model_name == "gemini-3.5-flash"
    assert settings.rag_candidate_k == 15
    assert settings.rag_rerank_enabled is True
    assert settings.reranker_model_name == "gemini-3.5-flash-lite"


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "On"])
def test_settings_accept_case_insensitive_rerank_boolean_values(
    monkeypatch: pytest.MonkeyPatch, value: str
):
    monkeypatch.setenv("AI_DATABASE_URL", "postgresql://test")
    monkeypatch.setenv("RAG_RERANK_ENABLED", value)

    assert Settings.from_env().rag_rerank_enabled is True


@pytest.mark.parametrize("value", ["0", "false", "off", "maybe"])
def test_settings_reject_other_non_empty_rerank_boolean_values(
    monkeypatch: pytest.MonkeyPatch, value: str
):
    monkeypatch.setenv("AI_DATABASE_URL", "postgresql://test")
    monkeypatch.setenv("RAG_RERANK_ENABLED", value)

    with pytest.raises(ValueError, match="RAG_RERANK_ENABLED"):
        Settings.from_env()


def test_text_document_is_chunked_with_metadata_and_checksum():
    content = ("Approved product information for Product A. " * 120).encode()

    prepared = prepare_document(content, "approved-label.txt", metadata())

    assert len(prepared.chunks) > 1
    assert prepared.checksum == hashlib.sha256(content).hexdigest()
    assert prepared.metadata.title == "Approved Label"
    assert prepared.chunks[0].ordinal == 0
    assert all(len(chunk.content) <= 1200 for chunk in prepared.chunks)


@pytest.mark.parametrize("filename", ["label.exe", "label.docx"])
def test_unsupported_document_type_is_rejected(filename: str):
    with pytest.raises(KnowledgeValidationError, match="Unsupported document type"):
        prepare_document(b"content", filename, metadata())


def test_invalid_utf8_is_rejected():
    with pytest.raises(KnowledgeValidationError, match="UTF-8"):
        prepare_document(b"\xff\xfe", "label.txt", metadata())


def test_empty_document_is_rejected():
    with pytest.raises(KnowledgeValidationError, match="extractable text"):
        prepare_document(b"   \n\t", "label.md", metadata())


def pdf_bytes(text: str | None = None, *, encrypted: bool = False) -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    if text is not None:
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {NameObject("/F1"): writer._add_object(font)}
                )
            }
        )
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("secret")
    writer.write(output)
    return output.getvalue()


def test_pdf_text_is_extracted_with_page_number():
    prepared = prepare_document(
        pdf_bytes("Approved PDF content"),
        "approved-label.pdf",
        metadata(),
    )

    assert prepared.media_type == "application/pdf"
    assert prepared.chunks[0].page == 1
    assert prepared.chunks[0].content == "Approved PDF content"


def test_encrypted_pdf_is_rejected():
    with pytest.raises(KnowledgeValidationError, match="Encrypted PDF"):
        prepare_document(
            pdf_bytes("Approved PDF content", encrypted=True),
            "approved-label.pdf",
            metadata(),
        )


def test_image_only_or_empty_pdf_is_rejected():
    with pytest.raises(KnowledgeValidationError, match="extractable text"):
        prepare_document(pdf_bytes(), "empty-label.pdf", metadata())


def test_oversized_document_is_rejected():
    with pytest.raises(KnowledgeValidationError, match="10 MB"):
        prepare_document(
            b"a" * (10_485_760 + 1),
            "label.txt",
            metadata(),
            max_bytes=10_485_760,
        )


def test_effective_date_must_not_follow_expiration_date():
    with pytest.raises(ValidationError):
        metadata(
            effective_date=date(2027, 1, 1),
            expiration_date=date(2026, 1, 1),
        )


def test_ingestion_batches_embeddings_and_saves_atomically():
    store = RecordingDocumentStore()
    embedder = FakeEmbedder([[0.1, 0.2, 0.3]])
    service = KnowledgeIngestionService(store, embedder, expected_dimension=3)

    document_id = service.ingest(b"Approved content", "label.txt", metadata())

    assert document_id == "document-1"
    assert embedder.document_calls == [["Approved content"]]
    assert len(store.saved) == 1
    assert store.saved[0][2:] == ("fake-embedding", 3)


def test_embedding_dimension_mismatch_is_rejected_before_storage():
    store = RecordingDocumentStore()
    service = KnowledgeIngestionService(
        store,
        FakeEmbedder([[0.1, 0.2]]),
        expected_dimension=1024,
    )

    with pytest.raises(EmbeddingConfigurationError, match="dimension"):
        service.ingest(b"Approved content", "label.txt", metadata())

    assert store.saved == []

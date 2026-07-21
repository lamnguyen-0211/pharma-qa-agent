"""Pharmaceutical document validation, extraction, chunking, and ingestion."""

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .providers import EmbeddingProvider
from .models import KnowledgeDocument

DEFAULT_MAX_BYTES = 10_485_760
CHUNK_SIZE = 1_200
CHUNK_OVERLAP = 200


class KnowledgeValidationError(ValueError):
    """Raised when a source document or its metadata cannot be indexed."""


class EmbeddingConfigurationError(RuntimeError):
    """Raised when an embedding provider does not match the configured schema."""


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=255)
    document_type: str = Field(min_length=1, max_length=100)
    product: str | None = Field(default=None, max_length=255)
    active_ingredient: str | None = Field(default=None, max_length=255)
    market: str | None = Field(default=None, max_length=100)
    jurisdiction: str | None = Field(default=None, max_length=100)
    language: str = Field(min_length=1, max_length=32)
    effective_date: date | None = None
    expiration_date: date | None = None
    version: str = Field(min_length=1, max_length=64)
    approval_status: str = Field(min_length=1, max_length=32)
    audience: str | None = Field(default=None, max_length=100)
    access_classification: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def dates_are_ordered(self) -> "DocumentMetadata":
        if (
            self.effective_date is not None
            and self.expiration_date is not None
            and self.effective_date > self.expiration_date
        ):
            raise ValueError("effective_date must not follow expiration_date")
        return self


@dataclass(frozen=True)
class PreparedChunk:
    ordinal: int
    page: int | None
    content: str


@dataclass(frozen=True)
class PreparedDocument:
    source_bytes: bytes
    original_filename: str
    media_type: str
    checksum: str
    metadata: DocumentMetadata
    chunks: list[PreparedChunk]


class DocumentStore(Protocol):
    def save_document(
        self,
        prepared: PreparedDocument,
        embeddings: list[list[float]],
        model_name: str,
        dimension: int,
    ) -> KnowledgeDocument:
        """Persist a document and return the stored document."""
        ...


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_pages(source_bytes: bytes, extension: str) -> tuple[str, list[tuple[int | None, str]]]:
    if extension in {".txt", ".md"}:
        try:
            text = source_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise KnowledgeValidationError("Text documents must use UTF-8 encoding.") from error
        media_type = "text/markdown" if extension == ".md" else "text/plain"
        return media_type, [(None, text)]

    if extension == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(source_bytes))
            if reader.is_encrypted:
                raise KnowledgeValidationError("Encrypted PDF documents are not supported.")
            return "application/pdf", [
                (page_number, page.extract_text() or "")
                for page_number, page in enumerate(reader.pages, start=1)
            ]
        except KnowledgeValidationError:
            raise
        except Exception as error:
            raise KnowledgeValidationError("The PDF document is malformed.") from error

    raise KnowledgeValidationError("Unsupported document type. Use PDF, TXT, or Markdown.")


def _chunk_page(text: str, page: int | None, ordinal: int) -> list[PreparedChunk]:
    chunks: list[PreparedChunk] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + CHUNK_SIZE // 2, end)
            if boundary > start:
                end = boundary
        content = text[start:end].strip()
        if content:
            chunks.append(PreparedChunk(ordinal + len(chunks), page, content))
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def prepare_document(
    source_bytes: bytes,
    filename: str,
    metadata: DocumentMetadata,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> PreparedDocument:
    if not source_bytes:
        raise KnowledgeValidationError("The document has no extractable text.")
    if len(source_bytes) > max_bytes:
        raise KnowledgeValidationError("Documents must be 10 MB or smaller.")

    safe_filename = Path(filename).name
    extension = Path(safe_filename).suffix.lower()
    media_type, pages = _extract_pages(source_bytes, extension)

    chunks: list[PreparedChunk] = []
    for page, page_text in pages:
        normalized = _normalized(page_text)
        chunks.extend(_chunk_page(normalized, page, len(chunks)))
    if not chunks:
        raise KnowledgeValidationError("The document has no extractable text.")

    return PreparedDocument(
        source_bytes=source_bytes,
        original_filename=safe_filename,
        media_type=media_type,
        checksum=hashlib.sha256(source_bytes).hexdigest(),
        metadata=metadata,
        chunks=chunks,
    )


class KnowledgeIngestionService:
    def __init__(
        self,
        store: DocumentStore,
        embedder: EmbeddingProvider,
        expected_dimension: int,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.expected_dimension = expected_dimension
        self.max_bytes = max_bytes

    def ingest(
        self,
        source_bytes: bytes,
        filename: str,
        metadata: DocumentMetadata,
    ):
        prepared = prepare_document(
            source_bytes,
            filename,
            metadata,
            max_bytes=self.max_bytes,
        )
        embeddings = self.embedder.embed_documents(
            [chunk.content for chunk in prepared.chunks]
        )
        if len(embeddings) != len(prepared.chunks) or any(
            len(vector) != self.expected_dimension for vector in embeddings
        ):
            raise EmbeddingConfigurationError(
                "Embedding dimension does not match EMBEDDING_DIMENSION."
            )
        return self.store.save_document(
            prepared,
            embeddings,
            self.embedder.model_name,
            self.expected_dimension,
        )

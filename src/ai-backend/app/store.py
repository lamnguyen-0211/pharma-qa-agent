"""AI-owned persistence for chat history and approved-document retrieval."""

import logging
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from .knowledge import EmbeddingConfigurationError, PreparedDocument
from .models import ChatResponse, KnowledgeDocument, RetrievedChunk
from .providers import EmbeddingProvider, KnowledgeReranker, ModelProviderError

logger = logging.getLogger(__name__)


class AiPersistenceError(RuntimeError):
    """Raised when AI state cannot be safely persisted or retrieved."""


class DuplicateDocumentError(AiPersistenceError):
    """Raised when a source checksum already exists."""


class AiStore(Protocol):
    def record_turn(
        self,
        chat_session_id: str | None,
        business_session_id: str,
        question: str,
        response: ChatResponse,
    ) -> str:
        """Persist a session and its USER/ASSISTANT message pair atomically."""


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in vector) + "]"


class PostgresAiStore:
    """PostgreSQL implementation of chat, document, and retrieval persistence."""

    DOCUMENT_COLUMNS = """
        id, original_filename, title, document_type, product, active_ingredient,
        market, jurisdiction, language, effective_date, expiration_date, version,
        approval_status, audience, access_classification, embedding_model_name,
        embedding_dimension, chunk_count, created_at
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def initialize_schema(self) -> None:
        """Apply every AI-owned migration in filename order."""
        migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
        try:
            import psycopg

            with psycopg.connect(self.database_url) as connection:
                with connection.cursor() as cursor:
                    for migration in sorted(migrations_dir.glob("*.sql")):
                        cursor.execute(
                            migration.read_text(encoding="utf-8"),
                            prepare=False,
                        )
        except Exception as error:
            raise AiPersistenceError("Unable to initialize AI persistence.") from error

    @classmethod
    def _document_from_row(cls, row) -> KnowledgeDocument:
        return KnowledgeDocument(
            document_id=str(row[0]),
            original_filename=row[1],
            title=row[2],
            document_type=row[3],
            product=row[4],
            active_ingredient=row[5],
            market=row[6],
            jurisdiction=row[7],
            language=row[8],
            effective_date=row[9],
            expiration_date=row[10],
            version=row[11],
            approval_status=row[12],
            audience=row[13],
            access_classification=row[14],
            embedding_model_name=row[15],
            embedding_dimension=row[16],
            chunk_count=row[17],
            created_at=row[18],
        )

    def save_document(
        self,
        prepared: PreparedDocument,
        embeddings: list[list[float]],
        model_name: str,
        dimension: int,
    ) -> KnowledgeDocument:
        """Insert a source and every chunk in one transaction."""
        document_id = uuid4()
        metadata = prepared.metadata
        try:
            import psycopg

            with psycopg.connect(self.database_url) as connection:
                with connection.transaction():
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            INSERT INTO knowledge_document (
                              id, checksum, original_filename, media_type, source_bytes,
                              byte_size, title, document_type, product, active_ingredient,
                              market, jurisdiction, language, effective_date, expiration_date,
                              version, approval_status, audience, access_classification,
                              embedding_model_name, embedding_dimension, chunk_count
                            ) VALUES (
                              %s, %s, %s, %s, %s,
                              %s, %s, %s, %s, %s,
                              %s, %s, %s, %s, %s,
                              %s, %s, %s, %s,
                              %s, %s, %s
                            )
                            RETURNING created_at
                            """,
                            (
                                document_id,
                                prepared.checksum,
                                prepared.original_filename,
                                prepared.media_type,
                                prepared.source_bytes,
                                len(prepared.source_bytes),
                                metadata.title,
                                metadata.document_type,
                                metadata.product,
                                metadata.active_ingredient,
                                metadata.market,
                                metadata.jurisdiction,
                                metadata.language,
                                metadata.effective_date,
                                metadata.expiration_date,
                                metadata.version,
                                metadata.approval_status,
                                metadata.audience,
                                metadata.access_classification,
                                model_name,
                                dimension,
                                len(prepared.chunks),
                            ),
                        )
                        created_at = cursor.fetchone()[0]
                        cursor.executemany(
                            """
                            INSERT INTO knowledge_chunk
                              (id, document_id, ordinal, source_page, content, embedding)
                            VALUES (%s, %s, %s, %s, %s, %s::vector)
                            """,
                            [
                                (
                                    uuid4(),
                                    document_id,
                                    chunk.ordinal,
                                    chunk.page,
                                    chunk.content,
                                    _vector_literal(embedding),
                                )
                                for chunk, embedding in zip(
                                    prepared.chunks, embeddings, strict=True
                                )
                            ],
                        )
            return KnowledgeDocument(
                document_id=str(document_id),
                original_filename=prepared.original_filename,
                title=metadata.title,
                document_type=metadata.document_type,
                product=metadata.product,
                active_ingredient=metadata.active_ingredient,
                market=metadata.market,
                jurisdiction=metadata.jurisdiction,
                language=metadata.language,
                effective_date=metadata.effective_date,
                expiration_date=metadata.expiration_date,
                version=metadata.version,
                approval_status=metadata.approval_status,
                audience=metadata.audience,
                access_classification=metadata.access_classification,
                embedding_model_name=model_name,
                embedding_dimension=dimension,
                chunk_count=len(prepared.chunks),
                created_at=created_at,
            )
        except Exception as error:
            constraint_name = getattr(getattr(error, "diag", None), "constraint_name", None)
            if getattr(error, "sqlstate", None) == "23505" and constraint_name == "knowledge_document_checksum_key":
                raise DuplicateDocumentError("Document content already exists.") from error
            raise AiPersistenceError("Unable to persist knowledge document.") from error

    def list_documents(self) -> list[KnowledgeDocument]:
        try:
            import psycopg

            with psycopg.connect(self.database_url) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"SELECT {self.DOCUMENT_COLUMNS} FROM knowledge_document ORDER BY created_at DESC"
                    )
                    return [self._document_from_row(row) for row in cursor.fetchall()]
        except Exception as error:
            raise AiPersistenceError("Unable to list knowledge documents.") from error

    def search_knowledge(
        self,
        question: str,
        embedding: list[float],
        top_k: int,
    ) -> list[RetrievedChunk]:
        vector = _vector_literal(embedding)
        try:
            import psycopg

            with psycopg.connect(self.database_url) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        WITH eligible AS (
                          SELECT
                            c.id, c.document_id, c.source_page, c.content, c.embedding,
                            c.textsearch, d.title, d.version
                          FROM knowledge_chunk c
                          JOIN knowledge_document d ON d.id = c.document_id
                          WHERE d.approval_status = 'APPROVED'
                            AND (d.effective_date IS NULL OR d.effective_date <= CURRENT_DATE)
                            AND (d.expiration_date IS NULL OR d.expiration_date >= CURRENT_DATE)
                        ),
                        vector_results AS (
                          SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> %s::vector) AS rank
                          FROM eligible
                          ORDER BY embedding <=> %s::vector
                          LIMIT %s
                        ),
                        query AS (
                          SELECT plainto_tsquery('simple', %s) AS value
                        ),
                        text_results AS (
                          SELECT id, ROW_NUMBER() OVER (
                            ORDER BY ts_rank_cd(textsearch, query.value) DESC
                          ) AS rank
                          FROM eligible, query
                          WHERE textsearch @@ query.value
                          ORDER BY ts_rank_cd(textsearch, query.value) DESC
                          LIMIT %s
                        )
                        SELECT
                          e.id, e.document_id, e.title, e.version, e.source_page, e.content,
                          COALESCE(1.0 / (60 + vr.rank), 0.0)
                            + COALESCE(1.0 / (60 + tr.rank), 0.0) AS score
                        FROM eligible e
                        LEFT JOIN vector_results vr ON vr.id = e.id
                        LEFT JOIN text_results tr ON tr.id = e.id
                        WHERE vr.id IS NOT NULL OR tr.id IS NOT NULL
                        ORDER BY score DESC, e.id
                        LIMIT %s
                        """,
                        (vector, vector, top_k, question, top_k, top_k),
                    )
                    return [
                        RetrievedChunk(
                            chunk_id=str(row[0]),
                            document_id=str(row[1]),
                            title=row[2],
                            version=row[3],
                            page=row[4],
                            content=row[5],
                            score=float(row[6]),
                        )
                        for row in cursor.fetchall()
                    ]
        except Exception as error:
            raise AiPersistenceError("Approved knowledge retrieval is unavailable.") from error

    def clear_knowledge_for_tests(self) -> None:
        """Remove knowledge rows in an explicitly configured test database."""
        try:
            import psycopg

            with psycopg.connect(self.database_url) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("TRUNCATE knowledge_document CASCADE")
        except Exception as error:
            raise AiPersistenceError("Unable to reset test knowledge data.") from error

    def record_turn(
        self,
        chat_session_id: str | None,
        business_session_id: str,
        question: str,
        response: ChatResponse,
    ) -> str:
        """Create or validate a session and persist both messages in one transaction."""
        try:
            import psycopg

            session_id = UUID(chat_session_id) if chat_session_id else uuid4()
            trace_id = UUID(response.trace_id) if response.trace_id else None

            with psycopg.connect(self.database_url) as connection:
                with connection.transaction():
                    with connection.cursor() as cursor:
                        if chat_session_id is None:
                            cursor.execute(
                                "INSERT INTO chat_session (id, business_session_id) VALUES (%s, %s)",
                                (session_id, business_session_id),
                            )
                        else:
                            cursor.execute(
                                "SELECT business_session_id FROM chat_session WHERE id = %s FOR UPDATE",
                                (session_id,),
                            )
                            row = cursor.fetchone()
                            if row is None:
                                raise AiPersistenceError("AI chat session was not found.")
                            if row[0] != business_session_id:
                                raise AiPersistenceError(
                                    "AI chat session belongs to another business session."
                                )

                        cursor.executemany(
                            """
                            INSERT INTO chat_message
                              (id, chat_session_id, role, content, risk_level, trace_id)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            [
                                (uuid4(), session_id, "USER", question, "LOW", None),
                                (
                                    uuid4(),
                                    session_id,
                                    "ASSISTANT",
                                    response.answer,
                                    response.risk_level.upper(),
                                    trace_id,
                                ),
                            ],
                        )
                        cursor.execute(
                            "UPDATE chat_session SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                            (session_id,),
                        )

            return str(session_id)
        except AiPersistenceError:
            raise
        except Exception as error:
            raise AiPersistenceError("Unable to persist AI chat turn.") from error


class PostgresKnowledgeRetriever:
    def __init__(
        self,
        store,
        embedder: EmbeddingProvider,
        expected_dimension: int,
        top_k: int,
        max_context_chars: int,
        *,
        candidate_k: int | None = None,
        reranker: KnowledgeReranker | None = None,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.expected_dimension = expected_dimension
        self.top_k = top_k
        self.max_context_chars = max_context_chars
        self.candidate_k = max(candidate_k or top_k, top_k)
        self.reranker = reranker

    def search(self, question: str) -> list[RetrievedChunk]:
        embedding = self.embedder.embed_query(question)
        if len(embedding) != self.expected_dimension:
            raise EmbeddingConfigurationError(
                "Embedding dimension does not match EMBEDDING_DIMENSION."
            )
        chunks = self.store.search_knowledge(question, embedding, self.candidate_k)
        try:
            if self.reranker is not None and chunks:
                chunks = self.reranker.rerank(question, chunks, self.top_k)
        except ModelProviderError:
            logger.warning(
                "Knowledge reranking failed; using hybrid ranking", exc_info=True
            )
        chunks = chunks[: self.top_k]
        selected: list[RetrievedChunk] = []
        used_chars = 0
        for chunk in chunks:
            if used_chars + len(chunk.content) > self.max_context_chars:
                break
            selected.append(chunk)
            used_chars += len(chunk.content)
        return selected

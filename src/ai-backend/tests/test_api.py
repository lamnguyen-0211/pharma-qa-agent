import asyncio
from collections import defaultdict
from datetime import datetime, timezone

import pytest
import anyio.to_thread
import httpx

from app.knowledge import EmbeddingConfigurationError, KnowledgeValidationError
from app.main import create_app
from app.models import ChatResponse, GeneratedAnswer, KnowledgeDocument, RetrievedChunk
from app.providers import ModelProviderError
from app.store import AiPersistenceError, DuplicateDocumentError
from app.workflow import PharmaAgent


class FakeAiStore:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.messages: dict[str, list[tuple[str, str]]] = defaultdict(list)

    def record_turn(
        self,
        chat_session_id: str | None,
        business_session_id: str,
        question: str,
        response: ChatResponse,
    ) -> str:
        if self.fail:
            raise AiPersistenceError("database unavailable")

        session_id = chat_session_id or f"ai-session-{len(self.messages) + 1}"
        self.messages[session_id].extend(
            [("USER", question), ("ASSISTANT", response.answer)]
        )
        return session_id

    def roles_for(self, chat_session_id: str) -> list[str]:
        return [role for role, _ in self.messages[chat_session_id]]


class RecordingRetriever:
    def __init__(self, chunks: list[RetrievedChunk] | None = None) -> None:
        self.chunks = chunks or []
        self.queries: list[str] = []

    def search(self, question: str) -> list[RetrievedChunk]:
        self.queries.append(question)
        return self.chunks


class StaticProvider:
    def generate(self, question: str, chunks) -> GeneratedAnswer:
        return GeneratedAnswer(answer="Grounded answer", cited_chunk_ids=[])


def knowledge_document() -> KnowledgeDocument:
    return KnowledgeDocument(
        document_id="document-1",
        original_filename="label.txt",
        title="Approved Label",
        document_type="PRODUCT_LABEL",
        product="Product A",
        language="en",
        version="3.2",
        approval_status="APPROVED",
        access_classification="INTERNAL",
        embedding_model_name="fake-embedding",
        embedding_dimension=1024,
        chunk_count=1,
        created_at=datetime(2026, 7, 18, tzinfo=timezone.utc),
    )


class FakeKnowledgeService:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls = []

    def ingest(self, source_bytes, filename, metadata):
        self.calls.append((source_bytes, filename, metadata))
        if self.error:
            raise self.error
        return knowledge_document()


class FakeDocumentStore:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def list_documents(self):
        if self.error:
            raise self.error
        return [knowledge_document()]


@pytest.fixture
def fake_store() -> FakeAiStore:
    return FakeAiStore()


@pytest.fixture
def direct_threadpool(monkeypatch: pytest.MonkeyPatch):
    async def run_sync_without_worker_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(anyio.to_thread, "run_sync", run_sync_without_worker_thread)


@pytest.fixture
def client(fake_store: FakeAiStore, direct_threadpool):
    return create_app(PharmaAgent(fake_store))


def post_chat(application, payload: dict[str, str]) -> httpx.Response:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post("/v1/chat", json=payload)

    return asyncio.run(send_request())


def request(application, method: str, path: str, **kwargs) -> httpx.Response:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send_request())


def valid_metadata() -> dict[str, str]:
    return {
        "title": "Approved Label",
        "documentType": "PRODUCT_LABEL",
        "product": "Product A",
        "language": "en",
        "version": "3.2",
        "approvalStatus": "APPROVED",
        "accessClassification": "INTERNAL",
    }


def knowledge_app(
    direct_threadpool,
    *,
    ingestion_error: Exception | None = None,
    list_error: Exception | None = None,
):
    ingestion = FakeKnowledgeService(ingestion_error)
    application = create_app(
        PharmaAgent(FakeAiStore()),
        ingestion=ingestion,
        document_store=FakeDocumentStore(list_error),
    )
    return application, ingestion


def test_chat_creates_then_reuses_ai_session(client, fake_store: FakeAiStore):
    first = post_chat(client, {"businessSessionId": "business-1", "question": "What is this?"})
    second = post_chat(client, {
        "businessSessionId": "business-1",
        "chatSessionId": first.json()["chatSessionId"],
        "question": "Can I take a dose?",
    })

    assert first.status_code == 200
    assert first.json()["businessSessionId"] == "business-1"
    assert second.status_code == 200
    assert second.json()["chatSessionId"] == first.json()["chatSessionId"]
    assert fake_store.roles_for(first.json()["chatSessionId"]) == [
        "USER",
        "ASSISTANT",
        "USER",
        "ASSISTANT",
    ]


def test_chat_returns_503_when_turn_persistence_fails(direct_threadpool):
    app = create_app(PharmaAgent(FakeAiStore(fail=True)))

    response = post_chat(app, {"businessSessionId": "business-1", "question": "What is this?"})

    assert response.status_code == 503
    assert response.json()["detail"] == "AI response persistence is unavailable."


def test_emergency_chat_response_remains_classified_as_emergency(client):
    response = post_chat(client, {
        "businessSessionId": "business-1",
        "question": "I have difficulty breathing after this medication.",
    })

    assert response.status_code == 200
    assert response.json()["risk_level"] == "emergency"


def test_chat_defaults_knowledge_base_to_true(direct_threadpool):
    retriever = RecordingRetriever(
        [
            RetrievedChunk(
                chunk_id="chunk-1",
                document_id="document-1",
                title="Approved Label",
                version="3.2",
                content="Product A approved use.",
                score=1.0,
            )
        ]
    )
    application = create_app(
        PharmaAgent(FakeAiStore(), retriever, StaticProvider())
    )

    response = post_chat(
        application,
        {"businessSessionId": "business-1", "question": "Product A?"},
    )

    assert response.status_code == 200
    assert retriever.queries == ["Product A?"]


def test_chat_forwards_disabled_knowledge_choice(direct_threadpool):
    retriever = RecordingRetriever()
    application = create_app(
        PharmaAgent(FakeAiStore(), retriever, StaticProvider())
    )

    response = post_chat(
        application,
        {
            "businessSessionId": "business-1",
            "question": "Product A?",
            "useKnowledgeBase": False,
        },
    )

    assert response.status_code == 200
    assert retriever.queries == []


def test_upload_indexes_and_lists_document(direct_threadpool):
    application, ingestion = knowledge_app(direct_threadpool)

    upload = request(
        application,
        "POST",
        "/v1/knowledge/documents",
        files={"file": ("label.txt", b"Approved content", "text/plain")},
        data=valid_metadata(),
    )
    listed = request(application, "GET", "/v1/knowledge/documents")

    assert upload.status_code == 201
    assert upload.json()["chunkCount"] == 1
    assert listed.status_code == 200
    assert listed.json()[0]["title"] == "Approved Label"
    assert ingestion.calls[0][0:2] == (b"Approved content", "label.txt")
    assert ingestion.calls[0][2].approval_status == "APPROVED"


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (DuplicateDocumentError("duplicate"), 409, "Document content already exists."),
        (
            KnowledgeValidationError("private validation detail"),
            422,
            "Document upload is invalid.",
        ),
        (
            EmbeddingConfigurationError("bad vector"),
            503,
            "Knowledge indexing is unavailable.",
        ),
        (AiPersistenceError("database"), 503, "Knowledge indexing is unavailable."),
    ],
)
def test_upload_maps_domain_errors_without_leaking_details(
    direct_threadpool,
    error,
    status_code,
    detail,
):
    application, _ = knowledge_app(direct_threadpool, ingestion_error=error)

    response = request(
        application,
        "POST",
        "/v1/knowledge/documents",
        files={"file": ("label.txt", b"Approved content", "text/plain")},
        data=valid_metadata(),
    )

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert str(error) not in response.text


def test_list_failure_returns_503_without_leaking_details(direct_threadpool):
    application, _ = knowledge_app(
        direct_threadpool,
        list_error=AiPersistenceError("private database detail"),
    )

    response = request(application, "GET", "/v1/knowledge/documents")

    assert response.status_code == 503
    assert response.json() == {"detail": "Knowledge documents are unavailable."}
    assert "private database detail" not in response.text


def test_model_provider_failure_returns_503(direct_threadpool):
    class FailingProvider:
        def generate(self, question, chunks):
            raise ModelProviderError("secret provider detail")

    application = create_app(
        PharmaAgent(FakeAiStore(), RecordingRetriever(), FailingProvider())
    )

    response = post_chat(
        application,
        {
            "businessSessionId": "business-1",
            "question": "General question",
            "useKnowledgeBase": False,
        },
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "AI response generation is unavailable."}
    assert "secret provider detail" not in response.text

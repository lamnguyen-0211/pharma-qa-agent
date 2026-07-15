import asyncio
from collections import defaultdict

import pytest
import anyio.to_thread
import httpx

from app.main import create_app
from app.models import ChatResponse
from app.store import AiPersistenceError
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

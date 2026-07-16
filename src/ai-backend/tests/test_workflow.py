from app.models import ChatResponse, GeneratedAnswer, RetrievedChunk
from app.workflow import PharmaAgent


class RecordingStore:
    def __init__(self) -> None:
        self.turns: list[tuple[str | None, str, str, ChatResponse]] = []

    def record_turn(
        self,
        chat_session_id: str | None,
        business_session_id: str,
        question: str,
        response: ChatResponse,
    ) -> str:
        self.turns.append((chat_session_id, business_session_id, question, response))
        return chat_session_id or "ai-session-1"


class RecordingRetriever:
    def __init__(self, chunks: list[RetrievedChunk] | None = None) -> None:
        self.chunks = chunks or []
        self.queries: list[str] = []

    def search(self, question: str) -> list[RetrievedChunk]:
        self.queries.append(question)
        return self.chunks


class RecordingProvider:
    def __init__(self, generated: GeneratedAnswer | None = None) -> None:
        self.generated = generated or GeneratedAnswer(answer="General answer")
        self.calls: list[tuple[str, list[RetrievedChunk] | None]] = []

    def generate(
        self,
        question: str,
        chunks: list[RetrievedChunk] | None,
    ) -> GeneratedAnswer:
        self.calls.append((question, chunks))
        return self.generated


def approved_chunk(chunk_id: str = "chunk-1") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id="document-1",
        title="Approved Label",
        version="3.2",
        page=4,
        content="Product A is approved for internal information work.",
        score=0.95,
    )


def build_agent(
    *,
    chunks: list[RetrievedChunk] | None = None,
    generated: GeneratedAnswer | None = None,
) -> tuple[PharmaAgent, RecordingStore, RecordingRetriever, RecordingProvider]:
    store = RecordingStore()
    retriever = RecordingRetriever(chunks)
    provider = RecordingProvider(generated)
    return PharmaAgent(store, retriever, provider), store, retriever, provider


def test_emergency_questions_bypass_retrieval_and_generation():
    agent, store, retriever, provider = build_agent(chunks=[approved_chunk()])

    result = agent.answer(
        chat_session_id=None,
        business_session_id="business-1",
        question="I have difficulty breathing after taking this medicine",
        use_knowledge_base=True,
    )

    assert result.risk_level == "emergency"
    assert "emergency services" in result.answer
    assert result.chat_session_id == "ai-session-1"
    assert retriever.queries == []
    assert provider.calls == []
    assert store.turns[0][1:3] == (
        "business-1",
        "I have difficulty breathing after taking this medicine",
    )


def test_knowledge_mode_retrieves_and_validates_citations():
    chunk = approved_chunk()
    agent, _, retriever, provider = build_agent(
        chunks=[chunk],
        generated=GeneratedAnswer(
            answer="Grounded answer",
            cited_chunk_ids=["chunk-1", "invented-chunk"],
        ),
    )

    result = agent.answer(None, "business-1", "What is Product A used for?", True)

    assert result.answer == "Grounded answer"
    assert retriever.queries == ["What is Product A used for?"]
    assert provider.calls == [("What is Product A used for?", [chunk])]
    assert [citation.chunk_id for citation in result.citations] == ["chunk-1"]
    assert result.citations[0].title == "Approved Label"
    assert result.citations[0].page == 4


def test_knowledge_mode_abstains_without_approved_evidence():
    agent, _, retriever, provider = build_agent(chunks=[])

    result = agent.answer(None, "business-1", "What is Unknown Product used for?", True)

    assert "approved evidence" in result.answer.lower()
    assert result.citations == []
    assert retriever.queries == ["What is Unknown Product used for?"]
    assert provider.calls == []


def test_general_mode_skips_retrieval_and_has_no_citations():
    agent, _, retriever, provider = build_agent(
        chunks=[approved_chunk()],
        generated=GeneratedAnswer(answer="General informational answer"),
    )

    result = agent.answer(None, "business-1", "Explain this topic", False)

    assert result.answer == "General informational answer"
    assert result.citations == []
    assert retriever.queries == []
    assert provider.calls == [("Explain this topic", None)]


def test_high_risk_questions_are_classified():
    agent, _, _, _ = build_agent()
    assert agent.classify("What is the dosage?") == "high"

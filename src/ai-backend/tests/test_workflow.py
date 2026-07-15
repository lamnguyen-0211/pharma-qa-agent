from app.models import ChatResponse
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


def test_emergency_questions_are_stopped_before_model_work():
    store = RecordingStore()
    result = PharmaAgent(store).answer(
        chat_session_id=None,
        business_session_id="business-1",
        question="I have difficulty breathing after taking this medicine",
    )

    assert result.risk_level == "emergency"
    assert "emergency services" in result.answer
    assert result.chat_session_id == "ai-session-1"
    assert store.turns[0][1:3] == (
        "business-1",
        "I have difficulty breathing after taking this medicine",
    )


def test_high_risk_questions_are_classified():
    assert PharmaAgent(RecordingStore()).classify("What is the dosage?") == "high"

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["low", "medium", "high", "emergency"]


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    business_session_id: str = Field(alias="businessSessionId", min_length=1, max_length=36)
    chat_session_id: str | None = Field(default=None, alias="chatSessionId", max_length=36)
    question: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    business_session_id: str = Field(alias="businessSessionId")
    chat_session_id: str = Field(alias="chatSessionId")
    answer: str
    risk_level: RiskLevel
    citations: list[str] = Field(default_factory=list)
    trace_id: str | None = None

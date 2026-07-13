from typing import Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["low", "medium", "high", "emergency"]


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    answer: str
    risk_level: RiskLevel
    citations: list[str] = Field(default_factory=list)
    trace_id: str | None = None

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["low", "medium", "high", "emergency"]


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    business_session_id: str = Field(alias="businessSessionId", min_length=1, max_length=36)
    chat_session_id: str | None = Field(default=None, alias="chatSessionId", max_length=36)
    question: str = Field(min_length=1, max_length=4000)
    use_knowledge_base: bool = Field(default=True, alias="useKnowledgeBase")


class Citation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    document_id: str = Field(alias="documentId")
    title: str
    version: str
    page: int | None = None
    chunk_id: str = Field(alias="chunkId")


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    version: str
    page: int | None = None
    content: str
    score: float


class GeneratedAnswer(BaseModel):
    answer: str
    cited_chunk_ids: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    business_session_id: str = Field(alias="businessSessionId")
    chat_session_id: str = Field(alias="chatSessionId")
    answer: str
    risk_level: RiskLevel
    citations: list[Citation] = Field(default_factory=list)
    trace_id: str | None = None

from datetime import date, datetime
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


class KnowledgeDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    document_id: str = Field(alias="documentId")
    original_filename: str = Field(alias="originalFilename")
    title: str
    document_type: str = Field(alias="documentType")
    product: str | None = None
    active_ingredient: str | None = Field(default=None, alias="activeIngredient")
    market: str | None = None
    jurisdiction: str | None = None
    language: str
    effective_date: date | None = Field(default=None, alias="effectiveDate")
    expiration_date: date | None = Field(default=None, alias="expirationDate")
    version: str
    approval_status: str = Field(alias="approvalStatus")
    audience: str | None = None
    access_classification: str = Field(alias="accessClassification")
    embedding_model_name: str = Field(alias="embeddingModelName")
    embedding_dimension: int = Field(alias="embeddingDimension")
    chunk_count: int = Field(alias="chunkCount")
    created_at: datetime = Field(alias="createdAt")


class ChatResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    business_session_id: str = Field(alias="businessSessionId")
    chat_session_id: str = Field(alias="chatSessionId")
    answer: str
    risk_level: RiskLevel
    citations: list[Citation] = Field(default_factory=list)
    trace_id: str | None = None

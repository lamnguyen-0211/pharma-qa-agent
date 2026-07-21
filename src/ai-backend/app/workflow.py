"""Deterministic LangGraph workflow for pharma chat and optional retrieval."""

import re
from typing import Literal, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from .models import Citation, ChatResponse, GeneratedAnswer, RetrievedChunk, RiskLevel
from .providers import (
    ChatProvider,
    EmptyKnowledgeRetriever,
    KnowledgeRetriever,
    UnconfiguredChatProvider,
)
from .store import AiStore

EMERGENCY = re.compile(r"chest pain|difficulty breathing|can't breathe|overdose|severe allergic", re.I)
HIGH_RISK = re.compile(r"dose|dosage|pregnan|side effect|contraindication|adverse", re.I)

EMERGENCY_ANSWER = (
    "This may be an emergency. Contact local emergency services or a qualified "
    "healthcare professional now. I cannot assess or treat an emergency."
)
NO_EVIDENCE_ANSWER = (
    "I could not find enough approved evidence in the knowledge base to answer that "
    "question. Please consult a qualified healthcare professional or an approved source."
)


class AgentState(TypedDict, total=False):
    business_session_id: str
    chat_session_id: str | None
    question: str
    use_knowledge_base: bool
    risk_level: RiskLevel
    retrieved_chunks: list[RetrievedChunk]
    generated: GeneratedAnswer
    answer: str
    citations: list[Citation]
    trace_id: str
    response: ChatResponse


class PharmaAgent:
    """Single orchestrator with deterministic safety and retrieval routing."""

    def __init__(
        self,
        store: AiStore,
        retriever: KnowledgeRetriever | None = None,
        provider: ChatProvider | None = None,
    ) -> None:
        self.store = store
        self.retriever = retriever or EmptyKnowledgeRetriever()
        self.provider = provider or UnconfiguredChatProvider()
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("classify_risk", self._classify_risk)
        builder.add_node("emergency_response", self._emergency_response)
        builder.add_node("retrieve_knowledge", self._retrieve_knowledge)
        builder.add_node("generate_grounded_response", self._generate_grounded_response)
        builder.add_node("generate_general_response", self._generate_general_response)
        builder.add_node("abstain", self._abstain)
        builder.add_node("persist_turn", self._persist_turn)
        builder.add_edge(START, "classify_risk")
        builder.add_conditional_edges("classify_risk", self._route_after_classification)
        builder.add_conditional_edges("retrieve_knowledge", self._route_after_retrieval)
        builder.add_edge("emergency_response", "persist_turn")
        builder.add_edge("generate_grounded_response", "persist_turn")
        builder.add_edge("generate_general_response", "persist_turn")
        builder.add_edge("abstain", "persist_turn")
        builder.add_edge("persist_turn", END)
        return builder.compile()

    def classify(self, question: str) -> RiskLevel:
        if EMERGENCY.search(question):
            return "emergency"
        if HIGH_RISK.search(question):
            return "high"
        return "low"

    def _classify_risk(self, state: AgentState) -> AgentState:
        return {"risk_level": self.classify(state["question"])}

    def _route_after_classification(
        self,
        state: AgentState,
    ) -> Literal["emergency_response", "retrieve_knowledge", "generate_general_response"]:
        if state["risk_level"] == "emergency":
            return "emergency_response"
        if state["use_knowledge_base"]:
            return "retrieve_knowledge"
        return "generate_general_response"

    def _retrieve_knowledge(self, state: AgentState) -> AgentState:
        return {"retrieved_chunks": self.retriever.search(state["question"])}

    def _route_after_retrieval(
        self,
        state: AgentState,
    ) -> Literal["generate_grounded_response", "abstain"]:
        return "generate_grounded_response" if state["retrieved_chunks"] else "abstain"

    def _emergency_response(self, state: AgentState) -> AgentState:
        return {"answer": EMERGENCY_ANSWER, "citations": []}

    def _generate_grounded_response(self, state: AgentState) -> AgentState:
        chunks = state["retrieved_chunks"]
        generated = self.provider.generate(state["question"], chunks)
        chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        citations: list[Citation] = []
        seen_ids: set[str] = set()
        for chunk_id in generated.cited_chunk_ids:
            chunk = chunks_by_id.get(chunk_id)
            if chunk is None or chunk_id in seen_ids:
                continue
            seen_ids.add(chunk_id)
            citations.append(
                Citation(
                    document_id=chunk.document_id,
                    title=chunk.title,
                    version=chunk.version,
                    page=chunk.page,
                    chunk_id=chunk.chunk_id,
                )
            )
        return {"answer": generated.answer, "citations": citations}

    def _generate_general_response(self, state: AgentState) -> AgentState:
        generated = self.provider.generate(state["question"], None)
        return {"answer": generated.answer, "citations": []}

    def _abstain(self, state: AgentState) -> AgentState:
        return {"answer": NO_EVIDENCE_ANSWER, "citations": []}

    def _persist_turn(self, state: AgentState) -> AgentState:
        response = ChatResponse(
            business_session_id=state["business_session_id"],
            chat_session_id="",
            answer=state["answer"],
            risk_level=state["risk_level"],
            citations=state["citations"],
            trace_id=state["trace_id"],
        )
        persisted_session_id = self.store.record_turn(
            state["chat_session_id"],
            state["business_session_id"],
            state["question"],
            response,
        )
        return {
            "response": response.model_copy(
                update={"chat_session_id": persisted_session_id}
            )
        }

    def answer(
        self,
        chat_session_id: str | None,
        business_session_id: str,
        question: str,
        use_knowledge_base: bool = True,
    ) -> ChatResponse:
        result = self.graph.invoke(
            {
                "business_session_id": business_session_id,
                "chat_session_id": chat_session_id,
                "question": question,
                "use_knowledge_base": use_knowledge_base,
                "trace_id": str(uuid4()),
            }
        )
        return result["response"]

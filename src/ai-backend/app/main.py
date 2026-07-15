import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request

from .models import ChatRequest, ChatResponse
from .store import AiPersistenceError, PostgresAiStore
from .workflow import PharmaAgent


def create_app(agent: PharmaAgent | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if agent is None:
            store = PostgresAiStore(os.environ["AI_DATABASE_URL"])
            store.initialize_schema()
            app.state.agent = PharmaAgent(store)
        else:
            app.state.agent = agent
        yield

    application = FastAPI(
        title="Pharma AI Agent Service",
        version="0.1.0",
        lifespan=lifespan,
    )
    if agent is not None:
        application.state.agent = agent

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "pharma-ai-agent"}

    @application.post("/v1/chat", response_model=ChatResponse)
    def chat(request: ChatRequest, raw_request: Request) -> ChatResponse:
        try:
            return raw_request.app.state.agent.answer(
                chat_session_id=request.chat_session_id,
                business_session_id=request.business_session_id,
                question=request.question,
            )
        except AiPersistenceError as error:
            raise HTTPException(
                status_code=503,
                detail="AI response persistence is unavailable.",
            ) from error

    return application

app = create_app()

from fastapi import FastAPI

from .models import ChatRequest, ChatResponse
from .workflow import PharmaAgent

app = FastAPI(title="Pharma AI Agent Service", version="0.1.0")
agent = PharmaAgent()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "pharma-ai-agent"}


@app.post("/v1/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return agent.answer(request.question)

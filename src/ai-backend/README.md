# Pharma AI Agent Service

This FastAPI service owns AI chat sessions, messages, provider/model configuration, versioned prompts, risk classification, and agent orchestration. The Next.js app is only a frontend gateway; it does not call an LLM provider.

```bash
cd src/ai-backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Run the service tests from this directory with `python -m pytest`.

Set `AI_DATABASE_URL` to a PostgreSQL database before starting the service. On startup, the service applies `migrations/001_ai_schema.sql`, which creates `chat_session`, `chat_message`, `llm_provider`, `llm_model`, `prompt`, and `prompt_version`.

The `POST /v1/chat` contract is:

```json
{
  "businessSessionId": "core-owned-id",
  "chatSessionId": "optional-ai-id",
  "question": "What is this product used for?"
}
```

The first request creates an AI-owned `chatSessionId`; later requests reuse it. Both message roles are persisted atomically before a successful response is returned.

The service intentionally does not accept a ChatGPT browser session or implement an unofficial OpenAI OAuth flow. OpenAI API model access requires supported API authentication; ChatGPT/Codex sign-in credentials are separate. Add a supported, approved model provider behind `ModelProvider` before enabling production model calls.

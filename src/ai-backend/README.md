# Pharma AI Agent Service

This FastAPI service owns risk classification and agent orchestration. The Next.js app is only a frontend gateway; it does not call an LLM provider.

```bash
cd src/ai-backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Run the service tests from this directory with `python -m pytest`.

The service intentionally does not accept a ChatGPT browser session or implement an unofficial OpenAI OAuth flow. OpenAI API model access requires supported API authentication; ChatGPT/Codex sign-in credentials are separate. Add a supported, approved model provider behind `ModelProvider` before enabling production model calls.

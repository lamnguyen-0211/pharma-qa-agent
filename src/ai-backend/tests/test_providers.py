from types import SimpleNamespace

import pytest
from google.genai import types

from app.models import RetrievedChunk
from app.providers import GeminiChatProvider, ModelProviderError


class FakeModels:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def sdk_response(text: str | None) -> types.GenerateContentResponse:
    parts = [] if text is None else [types.Part(text=text)]
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(parts=parts))]
    )


def approved_chunk(chunk_id: str = "chunk-1") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id="document-1",
        title="Approved Label",
        version="3.2",
        page=4,
        content="Product A is approved for internal information work.",
        score=1.0,
    )


def test_gemini_provider_requests_structured_grounded_output_and_filters_ids():
    models = FakeModels(
        sdk_response(
            '{"answer":"Supported answer",'
            '"cited_chunk_ids":["chunk-1","invented"]}'
        )
    )
    provider = GeminiChatProvider(
        "server-only-key",
        "gemini-test-model",
        client=SimpleNamespace(models=models),
    )

    result = provider.generate("What is Product A used for?", [approved_chunk()])

    assert result.answer == "Supported answer"
    assert result.cited_chunk_ids == ["chunk-1"]
    call = models.calls[0]
    assert call["model"] == "gemini-test-model"
    assert "chunk-1" in call["contents"]
    assert "Product A is approved" in call["contents"]
    assert "untrusted evidence" in call["contents"].lower()
    assert call["config"].response_mime_type == "application/json"
    assert call["config"].response_schema is not None


def test_gemini_general_mode_does_not_accept_citations():
    models = FakeModels(
        sdk_response('{"answer":"General answer","cited_chunk_ids":["invented"]}')
    )
    provider = GeminiChatProvider(
        "server-only-key",
        "gemini-test-model",
        client=SimpleNamespace(models=models),
    )

    result = provider.generate("Explain this topic", None)

    assert result.answer == "General answer"
    assert result.cited_chunk_ids == []
    assert "No retrieved evidence" in models.calls[0]["contents"]


@pytest.mark.parametrize(
    "response",
    [sdk_response("not json"), sdk_response(None)],
)
def test_gemini_provider_rejects_malformed_responses(response):
    provider = GeminiChatProvider(
        "server-only-key",
        "gemini-test-model",
        client=SimpleNamespace(models=FakeModels(response)),
    )

    with pytest.raises(ModelProviderError, match="valid structured response"):
        provider.generate("Question", [approved_chunk()])


def test_gemini_provider_wraps_sdk_failures():
    provider = GeminiChatProvider(
        "server-only-key",
        "gemini-test-model",
        client=SimpleNamespace(models=FakeModels(error=RuntimeError("api key leaked"))),
    )

    with pytest.raises(ModelProviderError, match="generation failed") as captured:
        provider.generate("Question", [approved_chunk()])

    assert "api key leaked" not in str(captured.value)

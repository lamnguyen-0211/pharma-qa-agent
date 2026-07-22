from types import SimpleNamespace

import pytest
from google.genai import types

from app.models import RetrievedChunk
from app.providers import GeminiChatProvider, GeminiReranker, ModelProviderError


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


def candidate_chunk(chunk_id: str, content: str) -> RetrievedChunk:
    return approved_chunk(chunk_id).model_copy(update={"content": content})


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


def test_gemini_reranker_orders_known_chunks_by_model_score():
    models = FakeModels(
        sdk_response(
            '{"results":[{"chunk_id":"chunk-2","score":0.91},'
            '{"chunk_id":"chunk-1","score":0.42}]}'
        )
    )
    provider = GeminiReranker(
        "server-only-key",
        "gemini-reranker-model",
        client=SimpleNamespace(models=models),
    )
    chunks = [
        candidate_chunk("chunk-1", "Product A indication content."),
        candidate_chunk("chunk-2", "Product A contraindication content."),
    ]

    result = provider.rerank("What are Product A contraindications?", chunks, top_k=2)

    assert [chunk.chunk_id for chunk in result] == ["chunk-2", "chunk-1"]
    assert [chunk.score for chunk in result] == [0.91, 0.42]
    call = models.calls[0]
    assert call["model"] == "gemini-reranker-model"
    assert "What are Product A contraindications?" in call["contents"]
    assert "Product A indication content." in call["contents"]
    assert "Product A contraindication content." in call["contents"]
    assert "untrusted" in call["contents"].lower()
    assert call["config"].response_mime_type == "application/json"
    assert call["config"].response_schema is not None


def test_gemini_reranker_discards_unknown_and_duplicate_chunk_ids():
    models = FakeModels(
        sdk_response(
            '{"results":[{"chunk_id":"invented","score":1.0},'
            '{"chunk_id":"chunk-1","score":0.8},'
            '{"chunk_id":"chunk-1","score":0.1},'
            '{"chunk_id":"chunk-2","score":0.7}]}'
        )
    )
    provider = GeminiReranker(
        "server-only-key",
        "gemini-reranker-model",
        client=SimpleNamespace(models=models),
    )

    result = provider.rerank(
        "Question",
        [approved_chunk("chunk-1"), approved_chunk("chunk-2")],
        top_k=2,
    )

    assert [chunk.chunk_id for chunk in result] == ["chunk-1", "chunk-2"]
    assert [chunk.score for chunk in result] == [0.8, 0.7]


@pytest.mark.parametrize(
    "response",
    [sdk_response("not json"), sdk_response(None)],
)
def test_gemini_reranker_rejects_malformed_response(response):
    provider = GeminiReranker(
        "server-only-key",
        "gemini-reranker-model",
        client=SimpleNamespace(models=FakeModels(response)),
    )

    with pytest.raises(ModelProviderError, match=r"Reranking failed\."):
        provider.rerank("Question", [approved_chunk()], top_k=1)


def test_gemini_reranker_rejects_response_without_known_ids():
    provider = GeminiReranker(
        "server-only-key",
        "gemini-reranker-model",
        client=SimpleNamespace(
            models=FakeModels(sdk_response('{"results":[{"chunk_id":"unknown","score":1.0}]}'))
        ),
    )

    with pytest.raises(ModelProviderError, match=r"Reranking failed\."):
        provider.rerank("Question", [approved_chunk()], top_k=1)


def test_gemini_reranker_wraps_sdk_failure_without_leaking_details():
    provider = GeminiReranker(
        "server-only-key",
        "gemini-reranker-model",
        client=SimpleNamespace(
            models=FakeModels(error=RuntimeError("reranker secret leaked"))
        ),
    )

    with pytest.raises(ModelProviderError, match=r"Reranking failed\.") as captured:
        provider.rerank("Question", [approved_chunk()], top_k=1)

    assert "reranker secret leaked" not in str(captured.value)

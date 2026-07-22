from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from pydantic import ValidationError

from .config import Settings
from .knowledge import (
    DocumentMetadata,
    EmbeddingConfigurationError,
    KnowledgeIngestionService,
    KnowledgeValidationError,
)
from .models import ChatRequest, ChatResponse, KnowledgeDocument
from .providers import (
    GeminiChatProvider,
    GeminiReranker,
    GoogleEmbeddingProvider,
    ModelProviderError,
    SentenceTransformerEmbeddingProvider,
)
from .store import (
    AiPersistenceError,
    DuplicateDocumentError,
    PostgresAiStore,
    PostgresKnowledgeRetriever,
)
from .workflow import PharmaAgent


def create_app(
    agent: PharmaAgent | None = None,
    *,
    ingestion=None,
    document_store=None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if agent is None:
            settings = Settings.from_env()
            store = PostgresAiStore(settings.ai_database_url)
            store.initialize_schema()

            if settings.embedding_type != "sentence-transformers":
                embedder = GoogleEmbeddingProvider(
                    api_key=settings.gemini_api_key,
                    model_name=settings.embedding_model_name,
                    output_dimensionality=settings.embedding_dimension,
                )

            else:
                embedder = SentenceTransformerEmbeddingProvider(
                    model_name=settings.embedding_model_name,
                    expected_dimension=settings.embedding_dimension,
                )

            reranker = None
            if settings.rag_rerank_enabled and settings.gemini_api_key:
                reranker = GeminiReranker(
                    settings.gemini_api_key,
                    settings.reranker_model_name,
                )
            retriever = PostgresKnowledgeRetriever(
                store,
                embedder,
                settings.embedding_dimension,
                settings.rag_top_k,
                settings.rag_max_context_chars,
                candidate_k=settings.rag_candidate_k,
                reranker=reranker,
            )
            provider = GeminiChatProvider(
                settings.gemini_api_key,
                settings.chat_model_name,
            )
            app.state.agent = PharmaAgent(store, retriever, provider)
            app.state.ingestion = KnowledgeIngestionService(
                store,
                embedder,
                settings.embedding_dimension,
                settings.knowledge_upload_max_bytes,
            )
            app.state.document_store = store
        else:
            app.state.agent = agent
            if ingestion is not None:
                app.state.ingestion = ingestion
            if document_store is not None:
                app.state.document_store = document_store
        yield

    application = FastAPI(
        title="Pharma AI Agent Service",
        version="0.1.0",
        lifespan=lifespan,
    )
    if agent is not None:
        application.state.agent = agent
    if ingestion is not None:
        application.state.ingestion = ingestion
    if document_store is not None:
        application.state.document_store = document_store

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
                use_knowledge_base=request.use_knowledge_base,
            )
        except ModelProviderError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI response generation is unavailable.",
            ) from error
        except AiPersistenceError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI response persistence is unavailable.",
            ) from error

    @application.post(
        "/v1/knowledge/documents",
        response_model=KnowledgeDocument,
        status_code=status.HTTP_201_CREATED,
    )
    async def upload_knowledge_document(
        raw_request: Request,
        file: UploadFile = File(...),
        title: str = Form(...),
        document_type: str = Form(..., alias="documentType"),
        product: str | None = Form(default=None),
        active_ingredient: str | None = Form(default=None, alias="activeIngredient"),
        market: str | None = Form(default=None),
        jurisdiction: str | None = Form(default=None),
        language: str = Form(...),
        effective_date: date | None = Form(default=None, alias="effectiveDate"),
        expiration_date: date | None = Form(default=None, alias="expirationDate"),
        version: str = Form(...),
        approval_status: str = Form(..., alias="approvalStatus"),
        audience: str | None = Form(default=None),
        access_classification: str = Form(..., alias="accessClassification"),
    ) -> KnowledgeDocument:
        try:
            metadata = DocumentMetadata(
                title=title,
                document_type=document_type,
                product=product,
                active_ingredient=active_ingredient,
                market=market,
                jurisdiction=jurisdiction,
                language=language,
                effective_date=effective_date,
                expiration_date=expiration_date,
                version=version,
                approval_status=approval_status,
                audience=audience,
                access_classification=access_classification,
            )
            source_bytes = await file.read()
            return raw_request.app.state.ingestion.ingest(
                source_bytes,
                file.filename or "",
                metadata,
            )
        except DuplicateDocumentError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Document content already exists.",
            ) from error
        except (KnowledgeValidationError, ValidationError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Document upload is invalid.",
            ) from error
        except (EmbeddingConfigurationError, AiPersistenceError) as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Knowledge indexing is unavailable.",
            ) from error
        finally:
            await file.close()

    @application.get(
        "/v1/knowledge/documents",
        response_model=list[KnowledgeDocument],
    )
    def list_knowledge_documents(raw_request: Request) -> list[KnowledgeDocument]:
        try:
            return raw_request.app.state.document_store.list_documents()
        except AiPersistenceError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Knowledge documents are unavailable.",
            ) from error

    return application

app = create_app()

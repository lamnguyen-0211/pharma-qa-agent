"""AI-owned persistence for chat history and provider configuration."""

from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from .models import ChatResponse


class AiPersistenceError(RuntimeError):
    """Raised when an AI turn cannot be safely persisted."""


class AiStore(Protocol):
    """Atomic persistence boundary for an AI chat turn."""

    def record_turn(
        self,
        chat_session_id: str | None,
        business_session_id: str,
        question: str,
        response: ChatResponse,
    ) -> str:
        """Persist a session and its USER/ASSISTANT message pair atomically."""


class PostgresAiStore:
    """PostgreSQL-backed implementation of the AI persistence boundary."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def initialize_schema(self) -> None:
        """Apply the AI-owned schema before serving production traffic."""
        schema_sql = (
            Path(__file__).resolve().parent.parent / "migrations" / "001_ai_schema.sql"
        ).read_text(encoding="utf-8")

        try:
            import psycopg

            with psycopg.connect(self.database_url) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(schema_sql, prepare=False)
        except Exception as error:
            raise AiPersistenceError("Unable to initialize AI persistence.") from error

    def record_turn(
        self,
        chat_session_id: str | None,
        business_session_id: str,
        question: str,
        response: ChatResponse,
    ) -> str:
        """Create or validate a session and persist both messages in one transaction."""
        try:
            import psycopg

            session_id = UUID(chat_session_id) if chat_session_id else uuid4()
            trace_id = UUID(response.trace_id) if response.trace_id else None

            with psycopg.connect(self.database_url) as connection:
                with connection.transaction():
                    with connection.cursor() as cursor:
                        if chat_session_id is None:
                            cursor.execute(
                                "INSERT INTO chat_session (id, business_session_id) VALUES (%s, %s)",
                                (session_id, business_session_id),
                            )
                        else:
                            cursor.execute(
                                "SELECT business_session_id FROM chat_session WHERE id = %s FOR UPDATE",
                                (session_id,),
                            )
                            row = cursor.fetchone()
                            if row is None:
                                raise AiPersistenceError("AI chat session was not found.")
                            if row[0] != business_session_id:
                                raise AiPersistenceError("AI chat session belongs to another business session.")

                        cursor.executemany(
                            """
                            INSERT INTO chat_message
                              (id, chat_session_id, role, content, risk_level, trace_id)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            [
                                (uuid4(), session_id, "USER", question, "LOW", None),
                                (
                                    uuid4(),
                                    session_id,
                                    "ASSISTANT",
                                    response.answer,
                                    response.risk_level.upper(),
                                    trace_id,
                                ),
                            ],
                        )
                        cursor.execute(
                            "UPDATE chat_session SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                            (session_id,),
                        )

            return str(session_id)
        except AiPersistenceError:
            raise
        except Exception as error:
            raise AiPersistenceError("Unable to persist AI chat turn.") from error

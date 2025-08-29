import os
from dataclasses import dataclass
from dotenv import load_dotenv


def load_env() -> None:
    # Load from .env if exists
    load_dotenv(override=False)


@dataclass(frozen=True)
class Settings:
    postgres_user: str
    postgres_password: str
    postgres_db: str
    pg_host: str
    pg_port: int
    database_url: str

    jina_api_key: str
    embedding_model: str
    embedding_dim: int
    rag_top_k: int

    openai_api_key: str
    openai_base_url: str
    openai_model: str

    user_input_max_tokens: int
    total_context_max_tokens: int
    history_max_tokens: int

    system_prompt: str

    @staticmethod
    def from_env() -> "Settings":
        load_env()
        return Settings(
            postgres_user=os.getenv("POSTGRES_USER", "memfuse"),
            postgres_password=os.getenv("POSTGRES_PASSWORD", "memfuse"),
            postgres_db=os.getenv("POSTGRES_DB", "memfuse"),
            pg_host=os.getenv("PGHOST", "localhost"),
            pg_port=int(os.getenv("PGPORT", "5432")),
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql://memfuse:memfuse@localhost:5432/memfuse",
            ),
            jina_api_key=os.getenv("JINA_API_KEY", ""),
            embedding_model=os.getenv("EMBEDDING_MODEL", "jina-embeddings-v3"),
            embedding_dim=int(os.getenv("EMBEDDING_DIM", "1024")),
            rag_top_k=int(os.getenv("RAG_TOP_K", "5")),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_base_url=os.getenv("OPENAI_BASE_URL", ""),
            openai_model=os.getenv("OPENAI_COMPATIBLE_MODEL", ""),
            user_input_max_tokens=int(os.getenv("USER_INPUT_MAX_TOKENS", "32000")),
            total_context_max_tokens=int(os.getenv("TOTAL_CONTEXT_MAX_TOKENS", "64000")),
            history_max_tokens=int(os.getenv("HISTORY_MAX_TOKENS", "16000")),
            system_prompt=os.getenv(
                "SYSTEM_PROMPT",
                "You are MemFuse, a helpful assistant. Use provided context.",
            ),
        )

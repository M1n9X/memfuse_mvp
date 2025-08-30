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
    openai_assistant_role: str

    user_input_max_tokens: int
    total_context_max_tokens: int
    history_max_tokens: int
    history_fetch_rounds: int
    retrieval_prefer_session: bool

    system_prompt: str

    # Phase 2 features
    structured_enabled: bool
    structured_top_k: int
    extractor_enabled: bool
    extractor_trigger_tokens: int
    extractor_dedup_top_k: int

    # Phase 4 features (Procedural Memory / Multi-Agent)
    m3_enabled: bool = False
    procedural_top_k: int = 5
    procedural_reuse_threshold: float = 0.9

    # Orchestrator controls
    planner_max_attempts: int = 3
    runs_base_dir: str = "runs"

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
            openai_assistant_role=os.getenv("OPENAI_ASSISTANT_ROLE", "assistant"),
            # Smaller defaults for easier demo; override in .env if needed
            user_input_max_tokens=int(os.getenv("USER_INPUT_MAX_TOKENS", "2048")),
            total_context_max_tokens=int(os.getenv("TOTAL_CONTEXT_MAX_TOKENS", "4096")),
            history_max_tokens=int(os.getenv("HISTORY_MAX_TOKENS", "1024")),
            history_fetch_rounds=int(os.getenv("HISTORY_FETCH_ROUNDS", "200")),
            retrieval_prefer_session=(os.getenv("RETRIEVAL_PREFER_SESSION", "true").lower() in {"1","true","yes","y"}),
            system_prompt=os.getenv(
                "SYSTEM_PROMPT",
                (
                    "You are MemFuse, a helpful assistant. Use provided context.\n"
                    "Follow these rules when forming your answer:\n"
                    "1) Prioritize the current user query at the end of the context.\n"
                    "2) Use [Retrieved Chunks] as external knowledge; cite relevant sources when possible.\n"
                    "3) [History summary (compressed)] captures truncated past turns; use it only for continuity.\n"
                    "4) Do not restate meta labels (like [Retrieved Chunks]); present a natural answer.\n"
                ),
            ),
            structured_enabled=(os.getenv("STRUCTURED_ENABLED", "false").lower() in {"1","true","yes","y"}),
            structured_top_k=int(os.getenv("STRUCTURED_TOP_K", "10")),
            extractor_enabled=(os.getenv("EXTRACTOR_ENABLED", "false").lower() in {"1","true","yes","y"}),
            extractor_trigger_tokens=int(os.getenv("EXTRACTOR_TRIGGER_TOKENS", "2000")),
            extractor_dedup_top_k=int(os.getenv("EXTRACTOR_DEDUP_TOP_K", "10")),
            # Phase 4 defaults
            m3_enabled=(os.getenv("M3_ENABLED", "false").lower() in {"1","true","yes","y"}),
            procedural_top_k=int(os.getenv("PROCEDURAL_TOP_K", "5")),
            procedural_reuse_threshold=float(os.getenv("PROCEDURAL_REUSE_THRESHOLD", "0.9")),
            planner_max_attempts=int(os.getenv("PLANNER_MAX_ATTEMPTS", "3")),
            runs_base_dir=os.getenv("RUNS_BASE_DIR", "runs"),
        )

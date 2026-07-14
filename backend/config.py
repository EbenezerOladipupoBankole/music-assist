"""
Centralized application configuration.

Every environment variable the backend reads lives here instead of being
scattered across main.py / rag_pipeline.py as ad-hoc os.getenv() calls.
"""
from functools import lru_cache
from typing import List, Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# CORS origins are places the *browser* runs from, not backend URLs - the old
# Cloud Run *.run.app entry that used to live here was the backend's own
# address, which a browser never sends as Origin. Deploy target is Render;
# see backend/render.yaml.
_DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "https://music-assists.web.app",
    "https://music-assists.firebaseapp.com",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core services
    openai_api_key: Optional[str] = None
    admin_key: Optional[str] = None
    environment: str = "development"
    port: int = 8000

    # RAG pipeline wiring
    vector_db_path: str = "./data/vector_store"
    llm_model: str = "gpt-4o-mini"

    # Conversation memory backend. SQLite needs no external service and is the
    # default; "firebase" requires Firestore credentials to be configured
    # (see firebase_memory.py) and is opt-in via this setting.
    memory_backend: Literal["sqlite", "firebase"] = "sqlite"

    # CORS - comma-separated extra origins, e.g. "my-app.example.com,foo.example.com"
    allowed_origins: Optional[str] = None

    # RAG pipeline tuning (formerly rag_pipeline.CONFIG)
    max_context_length: int = 3200
    max_retries: int = 3
    retry_base_delay: float = 0.5
    request_timeout: int = 45
    max_tokens: int = 1000
    temperature: float = 0.2
    chunk_size: int = 1000
    chunk_overlap: int = 150
    max_conversation_history: int = 10
    top_k_results: int = 5
    fetch_k_results: int = 20
    mmr_lambda: float = 0.6
    min_content_length_for_local: int = 400
    min_doc_length_for_web: int = 600
    cost_per_1k_input_tokens: float = 0.00015
    cost_per_1k_output_tokens: float = 0.0006

    @property
    def default_cors_origins(self) -> List[str]:
        """Base allow-list plus any extra origins configured via ALLOWED_ORIGINS."""
        origins = list(_DEFAULT_CORS_ORIGINS)
        if not self.allowed_origins:
            return origins

        for origin in self.allowed_origins.split(","):
            origin = origin.strip()
            if not origin:
                continue
            origins.append(origin)
            if not origin.startswith("http"):
                origins.append(f"https://{origin}")
                origins.append(f"http://{origin}")
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

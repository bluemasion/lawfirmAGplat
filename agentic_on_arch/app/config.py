"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    """Global settings — loaded from .env file or environment variables."""

    # --- App ---
    APP_NAME: str = "律所 AI 平台"
    APP_VERSION: str = "2.0.8"
    DEBUG: bool = True
    ENV: str = "dev"  # dev | test | prod

    # --- Server ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/lawfirm_ai"

    # --- JWT ---
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24h

    # --- LLM Providers ---
    CLAUDE_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

    QWEN_API_KEY: Optional[str] = None
    QWEN_MODEL: str = "qwen-max"

    GLM_API_KEY: Optional[str] = None
    GLM_MODEL: str = "glm-4"

    DEFAULT_LLM: str = "claude"  # claude | qwen | glm

    # --- RAG ---
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    TOP_K: int = 5

    # --- NER ---
    NER_MODE: str = "regex"  # regex | bert
    NER_LOG_ENABLED: bool = True

    # --- File Storage ---
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 50

    # --- CORS ---
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str
    app_version: str
    environment: str
    debug: bool

    log_level: str

    database_url: str

    runbooks_path: str
    embedding_model: str
    rag_chunk_size: int
    rag_chunk_overlap: int

    llm_provider: str
    llm_base_url: str
    llm_model: str

    executor_provider: str = "simulated"

    vector_store_provider: str
    vector_store_path: str

    seed_data_path: str

    airflow_base_url: str = "http://localhost:8080"
    airflow_username: str | None = None
    airflow_password: str | None = None

    airflow_timeout_seconds: float = 10.0
    airflow_max_retries: int = 3
    airflow_retry_delay_seconds: float = 1.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
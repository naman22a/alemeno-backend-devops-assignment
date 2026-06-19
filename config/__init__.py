from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Single source of truth for runtime config.

    Every value has a sane default so the app still boots if .env is
    missing, but docker-compose always passes an env_file explicitly.
    """

    database_url: str = "postgresql+psycopg2://localhost:postgres@postgres:5432/db"

    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"

    domestic_only_brands: str = "Swiggy,Ola,IRCTC,Zomato,RedBus,BookMyShow"

    upload_dir: str = "uploads"

    # LLM batching / retry knobs. Kept here (not hardcoded in services) so
    # they can be tuned per environment without a code change.
    llm_classification_batch_size: int = 25
    llm_max_retries: int = 3

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def domestic_brand_list(self) -> list[str]:
        return [b.strip().lower() for b in self.domestic_only_brands.split(",") if b.strip()]


settings = Settings()

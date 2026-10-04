from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLite default lets the stack run without Postgres for local dev/tests;
    # docker-compose (§6.2) always supplies the asyncpg URL.
    database_url: str = "sqlite+aiosqlite:///./dev.db"

    secret_key: str = "dev-insecure-secret-change-me"
    api_key_encryption_key: str = ""

    # Local Qwen 2.5 Coder 7B engine via Ollama
    ollama_base_url: str = "http://localhost:11434"
    default_grading_model: str = "qwen2.5-coder:7b"
    escalation_grading_model: str = "qwen2.5-coder:7b"
    grading_confidence_threshold: float = 0.6

    cors_origins: str = "http://localhost:5173"
    enable_background_jobs: bool = True

    media_root: str = "./media"
    # §12: externally-loadable plugins. Empty = disabled. Plugin code runs with
    # full backend privileges, so this is a self-host-only switch.
    plugin_dir: str = ""

    # §8.1 server-side URL fetching is an SSRF primitive: the user picks the
    # URL, the server makes the request. Non-public addresses are blocked
    # unless an operator deliberately opts in (e.g. an intranet wiki).
    url_fetch_enabled: bool = True
    url_fetch_allow_private: bool = False
    access_token_ttl_seconds: int = 60 * 60 * 24 * 14

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

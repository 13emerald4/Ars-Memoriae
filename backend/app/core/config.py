import os
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLite default lets the stack run without Postgres for local dev/tests;
    # docker-compose (§6.2) always supplies the asyncpg URL.
    database_url: str = "sqlite+aiosqlite:///./dev.db"

    # Signs login tokens. Left unset, a random key is generated on first start
    # and kept in secret_key_file, so no install runs on a publicly known key.
    secret_key: str = ""
    secret_key_file: str = "./.secret_key"

    # Local Qwen 2.5 Coder 7B engine via Ollama
    ollama_base_url: str = "http://localhost:11434"
    default_grading_model: str = "qwen2.5-coder:7b"
    escalation_grading_model: str = "qwen2.5-coder:7b"
    grading_confidence_threshold: float = 0.6
    # Card generation sends up to 8000 chars of passage plus instructions;
    # 2048 tokens truncated them. 8k costs ~0.5 GB of KV cache on a 7B model.
    ollama_num_ctx: int = 8192

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

    # Sign-up is open only until the first account exists. Code practice runs
    # user code on this machine, so on an instance reachable from outside
    # (the UBC tunnel, a LAN, a server) open sign-up would hand anyone who
    # finds the URL a way to run programs here. Set to 1 for a shared server.
    allow_registration: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


def _load_or_create_secret(path: Path) -> str:
    try:
        existing = path.read_text().strip()
    except FileNotFoundError:
        existing = ""
    if existing:
        return existing

    secret = secrets.token_urlsafe(48)
    try:
        # O_EXCL: if two processes start at once, the loser reads the
        # winner's key instead of overwriting it.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        existing = path.read_text().strip()
        if existing:
            return existing
        fd = os.open(path, os.O_WRONLY | os.O_TRUNC, 0o600)  # left empty by a crash
    with os.fdopen(fd, "w") as fh:
        fh.write(secret)
    return secret


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if not s.secret_key:
        s.secret_key = _load_or_create_secret(Path(s.secret_key_file))
    return s


settings = get_settings()

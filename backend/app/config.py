from __future__ import annotations

import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "La Vecchia Resto-Bar")
    env: str = os.getenv("APP_ENV", "dev")
    db_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")
    session_cookie: str = os.getenv("SESSION_COOKIE", "resto_session")
    session_idle_minutes: int = int(os.getenv("SESSION_IDLE_MINUTES", "30"))
    session_absolute_minutes: int = int(os.getenv("SESSION_ABSOLUTE_MINUTES", "720"))
    secret_key: str = os.getenv("SECRET_KEY", "dev-change-me")
    backups_dir: str = os.getenv("BACKUPS_DIR", "./data/backups")

settings = Settings()

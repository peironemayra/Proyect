from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path

from .config import settings

def ensure_data_dirs() -> None:
    # Database path for sqlite: sqlite:///./data/app.db
    if settings.db_url.startswith("sqlite"):
        db_path = settings.db_url.split("///")[-1]
        db_file = Path(db_path)
        if not db_file.is_absolute():
            db_file = Path.cwd() / db_file
        db_file.parent.mkdir(parents=True, exist_ok=True)

    backups = Path(settings.backups_dir)
    if not backups.is_absolute():
        backups = Path.cwd() / backups
    backups.mkdir(parents=True, exist_ok=True)

def backup_sqlite() -> str | None:
    if not settings.db_url.startswith("sqlite"):
        return None
    db_path = settings.db_url.split("///")[-1]
    db_file = Path(db_path)
    if not db_file.is_absolute():
        db_file = Path.cwd() / db_file
    if not db_file.exists():
        return None

    backups = Path(settings.backups_dir)
    if not backups.is_absolute():
        backups = Path.cwd() / backups
    backups.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = backups / f"app_{stamp}.db"
    shutil.copy2(db_file, out)
    return str(out)

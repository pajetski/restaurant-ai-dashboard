"""Environment-driven configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "claude-sonnet-5-5"


@dataclass(frozen=True)
class Config:
    data_dir: Path
    anthropic_api_key: str
    anthropic_model: str
    app_password: str
    app_env: str

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


def load_config(env: dict | None = None) -> Config:
    e = os.environ if env is None else env
    return Config(
        data_dir=Path(e.get("DATA_DIR", "data")),
        anthropic_api_key=e.get("ANTHROPIC_API_KEY", "").strip(),
        anthropic_model=e.get("ANTHROPIC_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        app_password=e.get("APP_PASSWORD", ""),
        app_env=e.get("APP_ENV", "development").strip().lower(),
    )

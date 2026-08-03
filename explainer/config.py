from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    for candidate in (Path.cwd() / ".env", REPO_ROOT / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=False)


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None
    anthropic_model: str
    anthropic_effort: str
    elevenlabs_api_key: str | None
    elevenlabs_voice_id: str | None
    elevenlabs_model_id: str
    tts_provider: str
    silent_cps: float
    projects_dir: Path

    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def has_elevenlabs(self) -> bool:
        return bool(self.elevenlabs_api_key and self.elevenlabs_voice_id)


@lru_cache(maxsize=1)
def settings() -> Settings:
    _load_env()
    projects = os.environ.get("EXPLAINER_PROJECTS_DIR", "projects")
    projects_path = Path(projects)
    if not projects_path.is_absolute():
        projects_path = (Path.cwd() / projects_path).resolve()
    return Settings(
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
        anthropic_model=os.environ.get("ANTHROPIC_MODEL", "claude-opus-5"),
        anthropic_effort=os.environ.get("ANTHROPIC_EFFORT", "high"),
        elevenlabs_api_key=os.environ.get("ELEVENLABS_API_KEY") or None,
        elevenlabs_voice_id=os.environ.get("ELEVENLABS_VOICE_ID") or None,
        elevenlabs_model_id=os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"),
        tts_provider=os.environ.get("EXPLAINER_TTS", "elevenlabs").strip().lower(),
        silent_cps=float(os.environ.get("EXPLAINER_SILENT_CPS", "14.5")),
        projects_dir=projects_path,
    )


def which(binary: str) -> str | None:
    return shutil.which(binary)

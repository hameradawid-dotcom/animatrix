from __future__ import annotations

import os

import pytest

from explainer.config import settings


@pytest.fixture()
def projekty(tmp_path, monkeypatch):
    """Izoluje katalog projektów na czas testu."""
    katalog = tmp_path / "projects"
    katalog.mkdir()
    monkeypatch.setenv("EXPLAINER_PROJECTS_DIR", str(katalog))
    monkeypatch.setenv("EXPLAINER_TTS", "silent")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    settings.cache_clear()
    yield katalog
    settings.cache_clear()
    os.environ.pop("EXPLAINER_PROJECTS_DIR", None)

from __future__ import annotations

import re
import shutil
from pathlib import Path

import yaml
from pydantic import BaseModel

from animatrix.config import settings
from animatrix.models import Costs, Scenes, Script, ScriptMeta, Storyboard

RUNTIME_DIR = Path(__file__).resolve().parent / "runtime"

SLUG_RE = re.compile(r"[^a-z0-9\-]+")


def slugify(name: str) -> str:
    table = str.maketrans("ąćęłńóśźż", "acelnoszz")
    s = name.strip().lower().translate(table)
    s = s.replace(" ", "-")
    s = SLUG_RE.sub("-", s).strip("-")
    return re.sub(r"-{2,}", "-", s) or "projekt"


def _dump(model: BaseModel, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = model.model_dump(mode="json")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    tmp.replace(path)


def _load(cls: type[BaseModel], path: Path):
    if not path.exists():
        return None
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return cls.model_validate(raw)


class ProjectError(RuntimeError):
    pass


class Project:
    def __init__(self, root: Path):
        self.root = root

    # --- ścieżki ---
    @property
    def name(self) -> str:
        return self.root.name

    @property
    def script_path(self) -> Path:
        return self.root / "script.yaml"

    @property
    def storyboard_path(self) -> Path:
        return self.root / "storyboard.yaml"

    @property
    def scenes_path(self) -> Path:
        return self.root / "scenes.yaml"

    @property
    def costs_path(self) -> Path:
        return self.root / "costs.yaml"

    @property
    def theme_path(self) -> Path:
        return self.root / "theme.py"

    @property
    def scenes_dir(self) -> Path:
        return self.root / "scenes"

    @property
    def previews_dir(self) -> Path:
        return self.root / "previews"

    @property
    def renders_dir(self) -> Path:
        return self.root / "renders"

    @property
    def output_dir(self) -> Path:
        return self.root / "output"

    @property
    def media_dir(self) -> Path:
        return self.root / "media"

    @property
    def assets_dir(self) -> Path:
        return self.root / "assets"

    @property
    def voice_cache_dir(self) -> Path:
        """Wspólny cache audio dla całego projektu — klucz to hash tekstu + konfiguracji
        głosu, więc rerender jednej sceny nie odświeża audio pozostałych."""
        return self.root / ".cache" / "voiceover"

    # --- tworzenie ---
    @classmethod
    def create(cls, name: str, meta: ScriptMeta) -> "Project":
        root = settings().projects_dir / slugify(name)
        if root.exists():
            raise ProjectError(f"Projekt {root} już istnieje.")
        proj = cls(root)
        for d in (
            proj.scenes_dir,
            proj.previews_dir,
            proj.renders_dir,
            proj.output_dir,
            proj.assets_dir,
            proj.voice_cache_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)
        proj.install_runtime()
        proj.save_script(Script(meta=meta))
        proj.save_costs(Costs())
        return proj

    @classmethod
    def open(cls, name: str) -> "Project":
        root = settings().projects_dir / slugify(name)
        if not root.exists():
            raise ProjectError(
                f"Nie znaleziono projektu '{name}' w {settings().projects_dir}. "
                "Użyj `animatrix projects`, żeby zobaczyć listę."
            )
        return cls(root)

    @staticmethod
    def list_all() -> list[str]:
        base = settings().projects_dir
        if not base.exists():
            return []
        return sorted(p.name for p in base.iterdir() if (p / "script.yaml").exists())

    def install_runtime(self, force: bool = False) -> list[str]:
        """Kopiuje theme.py i voice.py do projektu. theme.py jest własnością użytkownika —
        nie nadpisujemy go bez --force."""
        written: list[str] = []
        for src in sorted(RUNTIME_DIR.glob("*.py")):
            dst = self.root / src.name
            if dst.exists() and not force:
                continue
            self.root.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            written.append(src.name)
        return written

    # --- stan ---
    def load_script(self) -> Script:
        s = _load(Script, self.script_path)
        if s is None:
            raise ProjectError(f"Brak {self.script_path}. Uruchom `animatrix new`.")
        return s

    def save_script(self, script: Script) -> None:
        _dump(script, self.script_path)

    def load_storyboard(self) -> Storyboard:
        return _load(Storyboard, self.storyboard_path) or Storyboard()

    def save_storyboard(self, sb: Storyboard) -> None:
        _dump(sb, self.storyboard_path)

    def load_scenes(self) -> Scenes:
        return _load(Scenes, self.scenes_path) or Scenes()

    def save_scenes(self, sc: Scenes) -> None:
        _dump(sc, self.scenes_path)

    def load_costs(self) -> Costs:
        return _load(Costs, self.costs_path) or Costs()

    def save_costs(self, c: Costs) -> None:
        _dump(c, self.costs_path)

    def rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root))
        except ValueError:
            return str(path)

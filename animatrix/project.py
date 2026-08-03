from __future__ import annotations

import os
import re
import shutil
import time
from pathlib import Path

import yaml
from pydantic import BaseModel

from animatrix.config import settings
from animatrix.models import Costs, Scenes, Script, ScriptMeta, Storyboard

RUNTIME_DIR = Path(__file__).resolve().parent / "runtime"
DOMYSLNY_MOTYW = "kh"

SLUG_RE = re.compile(r"[^a-z0-9\-]+")


def dostepne_motywy() -> list[str]:
    return sorted(p.stem.removeprefix("motyw_") for p in RUNTIME_DIR.glob("motyw_*.py"))


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
    def specs_dir(self) -> Path:
        """Sceny deklaratywne (`sceny/sNN.yaml`). `scenes/` trzyma surowy Python."""
        return self.root / "sceny"

    def spec_path(self, seg_id: str) -> Path:
        return self.specs_dir / f"{seg_id}.yaml"

    @property
    def runner_path(self) -> Path:
        return self.root / "scena_ze_specu.py"

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
        proj.install_runtime(meta.motyw)
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

    def install_runtime(self, motyw: str = DOMYSLNY_MOTYW, force: bool = False) -> list[str]:
        """Kopiuje theme.py, voice.py i wybrany motyw do projektu.

        Pliki są własnością użytkownika — nie nadpisujemy ich bez --force.
        `motyw_<nazwa>.py` ląduje jako `motyw.py`, żeby sceny miały jeden
        stabilny import niezależnie od wybranej stylistyki.
        """
        if motyw not in dostepne_motywy():
            raise ProjectError(
                f"Nie znam motywu '{motyw}'. Dostępne: {', '.join(dostepne_motywy())}"
            )

        self.root.mkdir(parents=True, exist_ok=True)
        pary = [
            (RUNTIME_DIR / "theme.py", "theme.py"),
            (RUNTIME_DIR / "voice.py", "voice.py"),
            (RUNTIME_DIR / f"motyw_{motyw}.py", "motyw.py"),
        ]
        written: list[str] = []
        for src, nazwa in pary:
            dst = self.root / nazwa
            if dst.exists() and not force:
                continue
            shutil.copyfile(src, dst)
            written.append(nazwa)

        # Runner scen ze specu to maszyneria narzędzia, nie plik użytkownika —
        # nadpisujemy go zawsze, żeby projekt nie został na starej wersji.
        shutil.copyfile(RUNTIME_DIR / "scena_ze_specu.py", self.root / "scena_ze_specu.py")
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

    # --- blokada zapisu ---
    def blokada(self, *, timeout: float = 10.0):
        """Wyłączność na zapis do projektu.

        CLI pracował jednowątkowo, więc problemu nie było. Interfejs potrafi
        wysłać dwa żądania naraz — bez blokady drugie nadpisałoby YAML-a
        wczytanego przed pierwszym.
        """
        return _Blokada(self.root / ".animatrix.lock", timeout)

    def rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root))
        except ValueError:
            return str(path)


class BlokadaZajeta(ProjectError):
    pass


class _Blokada:
    """Blokada pliku oparta o `O_EXCL` — działa też między procesami.

    Trzymamy PID, żeby po zabitym procesie dało się odróżnić blokadę żywą od
    osieroconej; osierocona jest przejmowana, a nie czeka w nieskończoność.
    """

    def __init__(self, sciezka: Path, timeout: float):
        self.sciezka = sciezka
        self.timeout = timeout
        self._trzymam = False

    def _zywy(self) -> bool:
        try:
            pid = int(self.sciezka.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return False
        if pid == os.getpid():
            return True
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def __enter__(self) -> "_Blokada":
        koniec = time.monotonic() + self.timeout
        while True:
            try:
                self.sciezka.parent.mkdir(parents=True, exist_ok=True)
                fd = os.open(self.sciezka, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                self._trzymam = True
                return self
            except FileExistsError:
                if not self._zywy():
                    self.sciezka.unlink(missing_ok=True)
                    continue
                if time.monotonic() >= koniec:
                    raise BlokadaZajeta(
                        f"Projekt {self.sciezka.parent.name} jest zajęty przez inną operację."
                    )
                time.sleep(0.05)

    def __exit__(self, *_) -> None:
        if self._trzymam:
            self.sciezka.unlink(missing_ok=True)
            self._trzymam = False

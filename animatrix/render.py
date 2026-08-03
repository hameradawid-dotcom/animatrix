from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from animatrix.config import settings
from animatrix.project import Project

QUALITY_FLAG = {"l": "-ql", "m": "-qm", "h": "-qh", "k": "-qk"}

# Flagi jakości Manima ustawiają rozdzielczość poziomą. Dla pionu (TikTok,
# Instagram Reels, YouTube Shorts) podajemy ją jawnie przez -r, inaczej wyszłoby
# wideo 16:9 z czarnymi pasami.
FORMATY: dict[str, dict[str, tuple[int, int, int]]] = {
    "poziom": {
        "l": (854, 480, 15),
        "m": (1280, 720, 30),
        "h": (1920, 1080, 60),
        "k": (3840, 2160, 60),
    },
    "pion": {
        "l": (540, 960, 30),
        "m": (720, 1280, 30),
        "h": (1080, 1920, 30),
        "k": (2160, 3840, 30),
    },
}
DOMYSLNY_FORMAT = "poziom"


class RenderError(RuntimeError):
    pass


@dataclass
class RenderResult:
    ok: bool
    output: Path | None
    stdout: str
    stderr: str
    cmd: list[str]

    @property
    def tail(self) -> str:
        """Ostatnie linie stderr — to trafia do modelu w pętli samonaprawy."""
        lines = [ln for ln in self.stderr.splitlines() if ln.strip()]
        return "\n".join(lines[-60:])


def manim_command() -> list[str]:
    if importlib.util.find_spec("manim") is not None:
        return [sys.executable, "-m", "manim"]
    binary = shutil.which("manim")
    if binary:
        return [binary]
    raise RenderError(
        "Nie znaleziono Manima. Zainstaluj: pip install 'manim>=0.19' 'manim-voiceover[elevenlabs]'"
    )


def subprocess_env(project: Project, *, voice: bool) -> dict[str, str]:
    cfg = settings()
    env = dict(os.environ)

    project_root = str(project.root.resolve())
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = f"{project_root}{os.pathsep}{existing}" if existing else project_root

    env["ANIMATRIX_TTS"] = cfg.tts_provider if voice else "silent"
    env["ANIMATRIX_SILENT_CPS"] = str(cfg.silent_cps)
    env["ANIMATRIX_VOICE_CACHE"] = str(project.voice_cache_dir.resolve())

    if cfg.elevenlabs_api_key:
        env["ELEVENLABS_API_KEY"] = cfg.elevenlabs_api_key
        env["ELEVEN_API_KEY"] = cfg.elevenlabs_api_key
    if cfg.elevenlabs_voice_id:
        env["ELEVENLABS_VOICE_ID"] = cfg.elevenlabs_voice_id
    env["ELEVENLABS_MODEL_ID"] = cfg.elevenlabs_model_id

    # Manim bywa gadatliwy o brakującym ffmpeg-u w PATH podprocesu.
    env.setdefault("PYTHONUNBUFFERED", "1")
    return env


def _find_output(project: Project, name: str, *, still: bool) -> Path | None:
    root = project.media_dir / ("images" if still else "videos")
    if not root.exists():
        return None
    suffix = ".png" if still else ".mp4"
    kandydaci = [p for p in root.rglob(f"{name}{suffix}") if p.is_file()]
    if not kandydaci:
        return None
    return max(kandydaci, key=lambda p: p.stat().st_mtime)


def render(
    project: Project,
    scene_file: Path,
    class_name: str,
    *,
    quality: str = "l",
    still: bool = False,
    out_name: str | None = None,
    voice: bool = True,
    format: str = DOMYSLNY_FORMAT,
    timeout: int = 3600,
) -> RenderResult:
    """Renderuje jedną scenę. Zwraca wynik zamiast rzucać — pętla samonaprawy
    potrzebuje stderr, nie wyjątku."""
    out_name = out_name or scene_file.stem
    tryb = FORMATY.get(format, FORMATY[DOMYSLNY_FORMAT])
    szerokosc, wysokosc, fps = tryb.get(quality, tryb["l"])
    cmd = [
        *manim_command(),
        "render",
        QUALITY_FLAG.get(quality, "-ql"),
        "-r",
        f"{szerokosc},{wysokosc}",
        "--fps",
        str(fps),
        "--disable_caching",
        "--media_dir",
        str(project.media_dir),
        "--progress_bar",
        "none",
        "-v",
        "WARNING",
        "-o",
        out_name,
    ]
    if still:
        cmd.append("-s")
    else:
        cmd += ["--format", "mp4"]
    cmd += [str(scene_file), class_name]

    try:
        proc = subprocess.run(
            cmd,
            cwd=project.root,
            env=subprocess_env(project, voice=voice),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return RenderResult(False, None, exc.stdout or "", f"Render przekroczył {timeout}s.", cmd)

    output = _find_output(project, out_name, still=still) if proc.returncode == 0 else None
    ok = proc.returncode == 0 and output is not None
    stderr = proc.stderr
    if proc.returncode == 0 and output is None:
        stderr += "\nRender zakończył się kodem 0, ale nie znaleziono pliku wyjściowego."
    return RenderResult(ok, output, proc.stdout, stderr, cmd)


def copy_output(result: RenderResult, target: Path) -> Path:
    if result.output is None:
        raise RenderError("Brak pliku wyjściowego do skopiowania.")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(result.output, target)
    return target

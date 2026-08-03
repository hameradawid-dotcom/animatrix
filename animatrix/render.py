from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from animatrix import formaty
from animatrix.config import settings
from animatrix.project import Project

QUALITY_FLAG = {"l": "-ql", "m": "-qm", "h": "-qh", "k": "-qk"}

# Rozdzielczość i proporcje kadru trzyma animatrix/formaty.py — flagi jakości
# Manima ustawiają wyłącznie kadr poziomy, więc podajemy je jawnie przez -r.
DOMYSLNY_FORMAT = formaty.DOMYSLNY


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


def subprocess_env(project: Project, *, voice: bool, format: str = DOMYSLNY_FORMAT) -> dict[str, str]:
    cfg = settings()
    env = dict(os.environ)

    project_root = str(project.root.resolve())
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = f"{project_root}{os.pathsep}{existing}" if existing else project_root

    env["ANIMATRIX_FORMAT"] = formaty.znormalizuj(format)
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


def buduj_komende(
    project: Project,
    scene_file: Path,
    class_name: str,
    *,
    quality: str,
    still: bool,
    out_name: str,
    format: str,
    postep: bool = False,
) -> list[str]:
    szerokosc, wysokosc, fps = formaty.rozdzielczosc(format, quality)
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
        # Pasek postępu jest jedynym źródłem informacji „która animacja się
        # renderuje" — wyłączamy go tylko tam, gdzie nikt tego nie czyta.
        "display" if postep else "none",
        "-v",
        "WARNING",
        "-o",
        out_name,
    ]
    if still:
        cmd.append("-s")
    else:
        cmd += ["--format", "mp4"]
    return cmd + [str(scene_file), class_name]


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
    extra_env: dict[str, str] | None = None,
) -> RenderResult:
    """Renderuje jedną scenę. Zwraca wynik zamiast rzucać — pętla samonaprawy
    potrzebuje stderr, nie wyjątku."""
    out_name = out_name or scene_file.stem
    cmd = buduj_komende(
        project,
        scene_file,
        class_name,
        quality=quality,
        still=still,
        out_name=out_name,
        format=format,
    )

    env = subprocess_env(project, voice=voice, format=format)
    env.update(extra_env or {})

    try:
        proc = subprocess.run(
            cmd,
            cwd=project.root,
            env=env,
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


# --------------------------------------------------------------------------
# Render z postępem i anulowaniem
#
# `subprocess.run` wystarcza CLI, ale interfejs potrzebuje dwóch rzeczy, których
# ono nie daje: informacji, jak daleko zaszedł render, i możliwości przerwania go.
# Stąd `Popen` + czytanie stderr linia po linii.
# --------------------------------------------------------------------------
POSTEP_RE = re.compile(r"Animation (\d+)\D+?(\d+)%")


@dataclass
class Postep:
    animacja: int
    procent_animacji: int
    linia: str

    def ulamek(self, animacji_razem: int | None) -> float | None:
        """Postęp całej sceny, o ile wiemy, ile animacji ma w sobie."""
        if not animacji_razem:
            return None
        zrobione = self.animacja + self.procent_animacji / 100
        return max(0.0, min(1.0, zrobione / animacji_razem))


def render_strumieniowo(
    project: Project,
    scene_file: Path,
    class_name: str,
    *,
    quality: str = "l",
    still: bool = False,
    out_name: str | None = None,
    voice: bool = True,
    format: str = DOMYSLNY_FORMAT,
    extra_env: dict[str, str] | None = None,
    na_postep: "Callable[[Postep], None] | None" = None,
    anuluj: "Callable[[], bool] | None" = None,
) -> RenderResult:
    """To samo co `render`, ale raportuje postęp i daje się przerwać.

    `anuluj` jest odpytywane między liniami wyjścia; gdy zwróci True, zabijamy
    całą grupę procesów — sam Manim odpala ffmpeg, więc zabicie tylko rodzica
    zostawiłoby sierotę dopisującą do pliku.
    """
    out_name = out_name or scene_file.stem
    cmd = buduj_komende(
        project,
        scene_file,
        class_name,
        quality=quality,
        still=still,
        out_name=out_name,
        format=format,
        postep=True,
    )
    env = subprocess_env(project, voice=voice, format=format)
    env.update(extra_env or {})

    proc = subprocess.Popen(
        cmd,
        cwd=project.root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,
    )

    linie: list[str] = []
    przerwane = False
    assert proc.stdout is not None
    try:
        for linia in proc.stdout:
            linia = linia.rstrip()
            if linia:
                linie.append(linia)
            if na_postep is not None:
                dopasowanie = POSTEP_RE.search(linia)
                if dopasowanie:
                    na_postep(
                        Postep(int(dopasowanie.group(1)), int(dopasowanie.group(2)), linia)
                    )
            if anuluj is not None and anuluj():
                przerwane = True
                _ubij(proc)
                break
    finally:
        proc.stdout.close()
        proc.wait()

    wyjscie = "\n".join(linie)
    if przerwane:
        return RenderResult(False, None, "", wyjscie + "\nRender przerwany.", cmd)

    output = _find_output(project, out_name, still=still) if proc.returncode == 0 else None
    ok = proc.returncode == 0 and output is not None
    if proc.returncode == 0 and output is None:
        wyjscie += "\nRender zakończył się kodem 0, ale nie znaleziono pliku wyjściowego."
    return RenderResult(ok, output, "", wyjscie, cmd)


def _ubij(proc: subprocess.Popen) -> None:
    import signal

    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError, AttributeError):
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, AttributeError):
            proc.kill()

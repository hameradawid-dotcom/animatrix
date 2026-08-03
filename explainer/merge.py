from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class MergeError(RuntimeError):
    pass


def ffmpeg_binary() -> str:
    binary = shutil.which("ffmpeg")
    if not binary:
        raise MergeError("Nie znaleziono ffmpeg w PATH. Zainstaluj ffmpeg i spróbuj ponownie.")
    return binary


def _concat_list(files: list[Path], target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"file '{f.resolve().as_posix()}'" for f in files]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def concat(files: list[Path], output: Path, *, workdir: Path) -> Path:
    """Skleja sceny w jeden MP4 w podanej kolejności.

    Najpierw próbuje `-c copy` (bez rekompresji, sekundy). Jeśli strumienie
    scen się różnią — co zdarza się, gdy jedna scena została wyrenderowana
    w innej jakości — wraca do przekodowania.
    """
    if not files:
        raise MergeError("Brak scen do sklejenia.")
    for f in files:
        if not f.exists():
            raise MergeError(f"Brak pliku sceny: {f}")

    output.parent.mkdir(parents=True, exist_ok=True)
    lista = _concat_list(files, workdir / "concat.txt")
    baza = [ffmpeg_binary(), "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista)]

    copy_cmd = [*baza, "-c", "copy", str(output)]
    proc = subprocess.run(copy_cmd, capture_output=True, text=True)
    if proc.returncode == 0 and output.exists() and output.stat().st_size > 0:
        return output

    reenc_cmd = [
        *baza,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output),
    ]
    proc2 = subprocess.run(reenc_cmd, capture_output=True, text=True)
    if proc2.returncode != 0:
        raise MergeError(
            "ffmpeg nie sklei scen.\n"
            f"-c copy: {proc.stderr.strip()[-800:]}\n"
            f"reencode: {proc2.stderr.strip()[-800:]}"
        )
    return output


def duration(path: Path) -> float | None:
    probe = shutil.which("ffprobe")
    if not probe:
        return None
    proc = subprocess.run(
        [probe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return None

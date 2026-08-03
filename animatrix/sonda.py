"""Pomiar układu sceny BEZ renderowania.

Render jednej sceny to kilkanaście sekund, a układ da się zmierzyć w ~2 s:
importujemy moduł sceny, podmieniamy lektora i `play` na atrapy, wykonujemy
`construct()` i odczytujemy prostokąty obiektów po każdym takcie.

Dzięki temu walidator odpowiada, zanim ruszy render — a nie po nim.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from animatrix import formaty
from animatrix.project import Project
from animatrix.render import manim_command, subprocess_env
from animatrix.uklad import Element, Kadr, Prostokat, Uchybienie, waliduj

RUNNER = Path(__file__).resolve().parent / "_sonda_runner.py"


class SondaError(RuntimeError):
    pass


@dataclass
class PomiarSceny:
    id: str
    format: str
    takty: int
    elementy: list[Element]
    uchybienia: list[Uchybienie]
    blad: str | None = None

    @property
    def ok(self) -> bool:
        return self.blad is None and not any(u.waga == "blad" for u in self.uchybienia)


def zmierz(
    project: Project,
    plik: Path,
    klasa: str,
    *,
    format: str,
    timeout: int = 180,
) -> PomiarSceny:
    """Uruchamia sondę w osobnym procesie.

    Osobny proces jest konieczny, bo `theme.py` ustawia globalny `config` Manima
    przy imporcie — zmierzenie dwóch formatów w jednym procesie dałoby skażony
    drugi wynik.
    """
    fmt = formaty.format_wideo(format)
    env = subprocess_env(project, voice=False, format=format)
    env["ANIMATRIX_SONDA_PLIK"] = str(plik)
    env["ANIMATRIX_SONDA_KLASA"] = klasa
    env["ANIMATRIX_SONDA_W"] = str(fmt.szerokosc)
    env["ANIMATRIX_SONDA_H"] = str(fmt.wysokosc)

    komenda = manim_command()
    python = komenda[0] if komenda[0] != "manim" else sys.executable

    try:
        proc = subprocess.run(
            [python, str(RUNNER)],
            cwd=project.root,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return PomiarSceny(klasa, format, 0, [], [], blad=f"pomiar przekroczył {timeout}s")

    if proc.returncode != 0:
        ogon = "\n".join(l for l in proc.stderr.splitlines() if l.strip())[-1200:]
        return PomiarSceny(klasa, format, 0, [], [], blad=ogon or "sonda zakończyła się błędem")

    try:
        dane = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        return PomiarSceny(klasa, format, 0, [], [], blad=f"sonda nie zwróciła JSON-a: {exc}")

    if dane.get("blad"):
        return PomiarSceny(klasa, format, 0, [], [], blad=dane["blad"])

    elementy = [
        Element(
            id=e["id"],
            prostokat=Prostokat(*e["prostokat"]),
            tekst=e["tekst"],
            rozmiar_px=e.get("rozmiar_px"),
        )
        for e in dane["elementy"]
    ]
    kadr = Kadr.z_formatu(format)
    return PomiarSceny(
        id=dane.get("scena", klasa),
        format=format,
        takty=dane.get("takty", 0),
        elementy=elementy,
        uchybienia=waliduj(elementy, kadr),
    )


def zmierz_projekt(project: Project, *, format: str | None = None) -> list[PomiarSceny]:
    from animatrix.stages import scenes as stage_scenes

    script = project.load_script()
    fmt = format or script.meta.format_wideo
    stan = stage_scenes.synchronizuj(project, script)

    wyniki: list[PomiarSceny] = []
    for st in stan.segmenty:
        plik = project.root / st.plik
        if not plik.exists():
            wyniki.append(
                PomiarSceny(st.id, fmt, 0, [], [], blad=f"brak pliku sceny {st.plik}")
            )
            continue
        pomiar = zmierz(project, plik, st.klasa, format=fmt)
        pomiar.id = st.id
        wyniki.append(pomiar)
    return wyniki

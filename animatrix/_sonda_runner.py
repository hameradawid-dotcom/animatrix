"""Wnętrze sondy — uruchamiane w OSOBNYM procesie przez `animatrix.sonda`.

Nie importuj tego modułu bezpośrednio: ustawia globalny `config` Manima
i podmienia metody `Scene`, więc skaziłby proces wywołujący.

Na stdout wypisuje jedną linię JSON-a z prostokątami obiektów sceny.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import traceback


def _wypisz(dane: dict) -> None:
    print(json.dumps(dane, ensure_ascii=False))


def main() -> int:
    plik = os.environ["ANIMATRIX_SONDA_PLIK"]
    klasa_nazwa = os.environ["ANIMATRIX_SONDA_KLASA"]
    szerokosc = int(os.environ.get("ANIMATRIX_SONDA_W", "1920"))
    wysokosc = int(os.environ.get("ANIMATRIX_SONDA_H", "1080"))

    os.environ.setdefault("ANIMATRIX_TTS", "silent")

    from manim import config

    # Kadr musi być ustawiony ZANIM zaimportuje się theme.py sceny — inaczej
    # zmierzymy kompozycję w złych proporcjach.
    config.pixel_width = szerokosc
    config.pixel_height = wysokosc
    config.frame_height = 8.0
    config.frame_width = 8.0 * szerokosc / wysokosc

    import manim

    takty = {"licznik": 0}
    stany: list = []

    def _widoczny(m) -> bool:
        """VGroup nie ma własnych punktów — trzymają je dzieci. ValueTracker ma
        punkty, ale nic nie rysuje: liczylibyśmy go jako obiekt w kadrze."""
        from manim import ValueTracker

        if isinstance(m, ValueTracker):
            return False
        try:
            if not m.family_members_with_points():
                return False
            return m.width > 1e-4 or m.height > 1e-4
        except Exception:
            return False

    def _rozwin(m, limit: int = 400) -> list:
        """Rozkłada zwykłe VGroup na dzieci.

        Bez tego walidator widzi tylko prostokąt opisany na całej grupie —
        a napisy nachodzące na siebie WEWNĄTRZ jednej grupy (etykieta osi vs
        wartość punktu) chowają się w takim prostokącie bez śladu. `Text` czy
        `MathTex` też są technicznie grupami glifów, więc rozwijamy wyłącznie
        czyste VGroup.
        """
        from manim import VGroup

        if type(m) is not VGroup:
            return [m]
        wynik = []
        for dziecko in m.submobjects:
            if not _widoczny(dziecko):
                continue
            wynik.extend(_rozwin(dziecko, limit))
            if len(wynik) >= limit:
                break
        return wynik or [m]

    def _zapamietaj(scena) -> None:
        widoczne = [m for m in scena.mobjects if _widoczny(m)]
        rozwiniete: list = []
        for m in widoczne:
            rozwiniete.extend(_rozwin(m))
        stany.append(rozwiniete)

    def _play(self, *animacje, **kw):
        takty["licznik"] += 1
        # Dokładamy końcowe obiekty animacji, bo `self.mobjects` jeszcze ich nie ma.
        for a in animacje:
            cel = getattr(a, "mobject", None)
            if cel is not None and cel not in self.mobjects:
                self.add(cel)
        _zapamietaj(self)

    def _wait(self, *a, **kw):
        return None

    manim.Scene.play = _play
    manim.Scene.wait = _wait

    # Lektor: żadnych połączeń, żadnego audio — tylko obiekt z .duration.
    try:
        from manim_voiceover import VoiceoverScene

        class _Tracker:
            duration = 6.0

        class _Kontekst:
            def __enter__(self):
                return _Tracker()

            def __exit__(self, *a):
                return False

        VoiceoverScene.set_speech_service = lambda self, *a, **kw: None
        VoiceoverScene.voiceover = lambda self, *a, **kw: _Kontekst()
    except ImportError:
        pass

    spec = importlib.util.spec_from_file_location("_scena_sondy", plik)
    if spec is None or spec.loader is None:
        _wypisz({"blad": f"nie da się zaimportować {plik}"})
        return 1
    modul = importlib.util.module_from_spec(spec)
    sys.modules["_scena_sondy"] = modul

    try:
        spec.loader.exec_module(modul)
        klasa = getattr(modul, klasa_nazwa)
        scena = klasa()
        scena.construct()
    except Exception:
        _wypisz({"blad": traceback.format_exc(limit=6)[-1500:]})
        return 0

    if not stany:
        _zapamietaj(scena)

    from manim import DOWN, LEFT, RIGHT, UP
    from manim import MarkupText, MathTex, Tex, Text

    px_na_jednostke = wysokosc / 8.0
    ostatni = stany[-1] if stany else []
    elementy = []
    for i, m in enumerate(ostatni):
        try:
            lewo, dol = m.get_corner(DOWN + LEFT)[:2]
            prawo, gora = m.get_corner(UP + RIGHT)[:2]
        except Exception:
            continue
        if not all(map(lambda v: v == v, (lewo, dol, prawo, gora))):  # NaN
            continue
        tekst = isinstance(m, (Text, MarkupText, MathTex, Tex))
        elementy.append(
            {
                "id": f"{type(m).__name__}#{i}",
                "prostokat": [float(lewo), float(dol), float(prawo), float(gora)],
                "tekst": bool(tekst),
                "rozmiar_px": float(m.height) * px_na_jednostke if tekst else None,
            }
        )

    _wypisz({"scena": klasa_nazwa, "takty": takty["licznik"], "elementy": elementy})
    return 0


if __name__ == "__main__":
    sys.exit(main())

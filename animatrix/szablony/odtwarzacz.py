"""Odtwarzanie specu sceny w Manimie.

Uruchamiane WYŁĄCZNIE w podprocesie renderu (albo sondy), gdzie na PYTHONPATH
jest katalog projektu — stąd `import theme` bez pakietu.
"""

from __future__ import annotations

import os
from pathlib import Path

from animatrix import scena as scena_mod
from animatrix.szablony import szablon
from animatrix.szablony.baza import Kontekst, naglowek_sekcji, tempo, zloz

ZMIENNA_SPECU = "ANIMATRIX_SPEC"


def _dane_projektu():
    try:
        import dane  # type: ignore

        return dane
    except ImportError:
        return None


def wczytaj_spec_ze_srodowiska():
    sciezka = os.environ.get(ZMIENNA_SPECU)
    if not sciezka:
        raise RuntimeError(
            f"Brak {ZMIENNA_SPECU} — scena ze specu musi dostać ścieżkę do pliku YAML."
        )
    return scena_mod.wczytaj(Path(sciezka))


def zbuduj(scene, spec=None):
    """Buduje kompozycję i zwraca (elementy, beaty, narracja)."""
    import theme as t  # type: ignore

    spec = spec or wczytaj_spec_ze_srodowiska()
    szab = szablon(spec.szablon)
    parametry = szab.Parametry.model_validate(spec.parametry)

    kontekst = Kontekst(t=t, kadr=t.kadr_sceny(), spec=spec, dane=_dane_projektu())
    komp = szab.zbuduj(kontekst, parametry)
    naglowek = naglowek_sekcji(kontekst)
    elementy = zloz(kontekst, komp, naglowek)

    moze_nachodzic = tuple(komp.moze_nachodzic) + tuple(spec.moze_nachodzic)
    t.sprawdz_uklad(elementy, moze_nachodzic=moze_nachodzic)

    beaty = tempo(komp, spec)
    if naglowek is not None and beaty:
        pierwszy = beaty[0]
        oryginalna = pierwszy.fabryka

        def z_naglowkiem(sc, oryginalna=oryginalna):
            anim = list(oryginalna(sc) or [])
            return [t.wejscie(naglowek), *anim]

        pierwszy.fabryka = z_naglowkiem

    return elementy, beaty, spec


def odegraj(scene, spec=None) -> None:
    import theme as t  # type: ignore

    elementy, beaty, spec = zbuduj(scene, spec)
    suma = sum(b.udzial for b in beaty) or 1.0

    with scene.voiceover(text=spec.narracja) as tracker:
        for beat in beaty:
            czas = tracker.duration * beat.udzial / suma
            animacje = beat.fabryka(scene)
            if not animacje:
                scene.wait(czas)
                continue
            kwargs = {"run_time": czas}
            if beat.rate_func is not None:
                kwargs["rate_func"] = beat.rate_func
            scene.play(*animacje, **kwargs)

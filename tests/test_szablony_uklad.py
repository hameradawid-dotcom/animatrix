"""Test tabelaryczny: każdy szablon musi się złożyć w kadrze, w każdym formacie.

To jest właściwy test regresji układu. Szablony budują się z przykładowych
parametrów, sonda mierzy prostokąty bez renderowania wideo, walidator sprawdza
kadr, strefę bezpieczną i kolizje. Tanio łapie dokładnie tę klasę usterek,
która wcześniej wychodziła dopiero po obejrzeniu gotowego filmu.
"""

from __future__ import annotations

import pytest

from animatrix import scena as scena_mod
from animatrix import sonda
from animatrix.models import ScriptMeta
from animatrix.project import Project
from animatrix.scena import SceneSpec
from animatrix.szablony import KATALOG
from animatrix.szablony.odtwarzacz import ZMIENNA_SPECU
from animatrix.uklad import bledy

pytest.importorskip("manim")
pytest.importorskip("manim_voiceover")

pytestmark = pytest.mark.slow

FORMATY = ["9:16", "16:9"]
NARRACJA = "Zdanie testowe, żeby scena miała z czego liczyć tempo."


@pytest.fixture(scope="module")
def _projekt_szablonow(tmp_path_factory):
    import os

    from animatrix.config import settings

    katalog = tmp_path_factory.mktemp("projekty")
    os.environ["ANIMATRIX_PROJECTS_DIR"] = str(katalog)
    os.environ["ANIMATRIX_TTS"] = "silent"
    settings.cache_clear()

    proj = Project.create("szablony-test", ScriptMeta(temat="test", motyw="misja"))
    for nazwa, szablon in KATALOG.items():
        spec = SceneSpec(
            id=nazwa,
            narracja=NARRACJA,
            szablon=nazwa,
            parametry=szablon.przyklad,
            sekcja={"numer": 1, "etykieta": "Sekcja testowa"},
        )
        scena_mod.zapisz(spec, proj.spec_path(nazwa))

    yield proj
    settings.cache_clear()
    os.environ.pop("ANIMATRIX_PROJECTS_DIR", None)


@pytest.mark.parametrize("nazwa", sorted(KATALOG))
@pytest.mark.parametrize("format_wideo", FORMATY)
def test_szablon_miesci_sie_w_kadrze(_projekt_szablonow, nazwa, format_wideo):
    proj = _projekt_szablonow
    pomiar = sonda.zmierz(
        proj,
        proj.runner_path,
        "ScenaZeSpecu",
        format=format_wideo,
        extra_env={ZMIENNA_SPECU: str(proj.spec_path(nazwa).resolve())},
    )
    assert pomiar.blad is None, f"{nazwa} @ {format_wideo}: {pomiar.blad}"
    assert pomiar.elementy, f"{nazwa} @ {format_wideo}: pusty kadr"
    assert pomiar.takty > 0, f"{nazwa} @ {format_wideo}: scena nic nie animuje"

    twarde = bledy(pomiar.uchybienia)
    assert not twarde, f"{nazwa} @ {format_wideo}: " + "; ".join(str(u) for u in twarde)

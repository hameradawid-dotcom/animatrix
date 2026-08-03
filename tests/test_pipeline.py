"""Test całego przepływu z podstawionym modelem.

Nie dzwoni do Anthropic ani do ElevenLabs, ale renderuje naprawdę — łącznie
z pętlą samonaprawy (pierwsza wersja kodu jest celowo zepsuta) i scaleniem
ffmpeg-iem. Wymaga zainstalowanego Manima; bez niego test się pomija.
"""

from __future__ import annotations

import pytest

from explainer.models import ScriptMeta
from explainer.project import Project
from explainer.stages import scenes as stage_scenes
from explainer.stages import script as stage_script
from explainer.stages import storyboard as stage_storyboard

pytest.importorskip("manim")
pytest.importorskip("manim_voiceover")

pytestmark = pytest.mark.slow

DOBRA_SCENA = '''\
from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = "{narracja}"


class {klasa}(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)
        napis = tytul("{napis}")
        with self.voiceover(text=NARRACJA) as tracker:
            self.play(FadeIn(napis), run_time=tracker.duration)
'''

ZEPSUTA_SCENA = '''\
from manim_voiceover import VoiceoverScene
from theme import *


class {klasa}(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)
        nie_ma_takiej_funkcji_w_manimie()
'''


class StubLLM:
    """Model, który za pierwszym razem pisze kod z błędem, a po komunikacie
    o błędzie zwraca wersję działającą."""

    def __init__(self, segmenty: list[tuple[str, str]], psuj_pierwsza: bool = True):
        self.segmenty = segmenty
        self.psuj_pierwsza = psuj_pierwsza
        self.zepsute: set[str] = set()
        self.wywolania_naprawy = 0

    def json_call(self, system: str, user: str, schema: dict, **kw) -> dict:
        if "segmenty" in schema.get("properties", {}) and "opis_wizualny" in str(schema):
            # etap 1 przenumerowuje segmenty na s01, s02, … — storyboard musi
            # odpowiadać tym identyfikatorom, nie surowym z briefu
            return {
                "segmenty": [
                    {
                        "id": f"s{i + 1:02d}",
                        "opis_wizualny": f"Napis {i + 1} pojawia się na środku.",
                        "obiekty": ["Text"],
                        "animacje": ["FadeIn"],
                        "assety": [],
                    }
                    for i in range(len(self.segmenty))
                ]
            }
        return {"segmenty": [{"id": sid, "narracja": narr} for sid, narr in self.segmenty]}

    def code_call(self, system: str, user: str, **kw) -> str:
        klasa = _klasa_z_promptu(user)
        if "Naprawa" in user or "Komunikat błędu" in user:
            self.wywolania_naprawy += 1
            return DOBRA_SCENA.format(klasa=klasa, narracja="Naprawiona scena.", napis="OK")
        if self.psuj_pierwsza and klasa not in self.zepsute:
            self.zepsute.add(klasa)
            return ZEPSUTA_SCENA.format(klasa=klasa)
        return DOBRA_SCENA.format(klasa=klasa, narracja="Poprawna scena.", napis="OK")


def _klasa_z_promptu(user: str) -> str:
    for token in user.replace(",", " ").split():
        if token.startswith("Scena_"):
            return token
    return "Scena_S01"


@pytest.fixture()
def projekt(projekty):
    proj = Project.create("pipeline", ScriptMeta(temat="test", docelowa_dlugosc_s=10))
    return proj


def test_etap1_generuje_i_numeruje_segmenty(projekt):
    llm = StubLLM([("x", "Pierwsze zdanie."), ("y", "Drugie zdanie.")])
    script = stage_script.generuj(projekt, llm)

    assert [s.id for s in script.segmenty] == ["s01", "s02"]
    assert script.segmenty[0].narracja == "Pierwsze zdanie."
    assert all(s.status == "draft" for s in script.segmenty)
    assert stage_script.suma_znakow(script) == len("Pierwsze zdanie.") + len("Drugie zdanie.")


def test_etap2_zachowuje_zaakceptowane_kadry(projekt):
    llm = StubLLM([("a", "Jeden."), ("b", "Dwa.")])
    script = stage_script.generuj(projekt, llm)
    for seg in script.segmenty:
        seg.status = "approved"
    projekt.save_script(script)

    sb = stage_storyboard.generuj(projekt, llm, script)
    sb.segmenty[0].opis_wizualny = "RĘCZNIE POPRAWIONY"
    sb.segmenty[0].status = "approved"
    projekt.save_storyboard(sb)

    znowu = stage_storyboard.generuj(projekt, llm, script)
    assert znowu.segmenty[0].opis_wizualny == "RĘCZNIE POPRAWIONY"
    assert znowu.segmenty[1].status == "draft"


def test_pelny_przeplyw_z_samonaprawa_i_scaleniem(projekt):
    llm = StubLLM([("a", "Pierwsza scena."), ("b", "Druga scena.")])

    script = stage_script.generuj(projekt, llm)
    for seg in script.segmenty:
        seg.status = "approved"
    projekt.save_script(script)

    sb = stage_storyboard.generuj(projekt, llm, script)
    for item in sb.segmenty:
        item.status = "approved"
    projekt.save_storyboard(sb)

    stan = stage_scenes.synchronizuj(projekt, script)
    for st in stan.segmenty:
        stage_scenes._generuj_kod(projekt, llm, script, sb, st)
        assert stage_scenes.renderuj_z_naprawa(projekt, llm, st, stan, max_prob=2)
        assert st.status == "rendered"
        assert st.proby_naprawy == 1  # pierwsza wersja była zepsuta
        assert (projekt.root / st.render_roboczy).exists()

    assert llm.wywolania_naprawy == 2

    for st in stan.segmenty:
        st.status = "approved"
    projekt.save_scenes(stan)

    wyjscie = stage_scenes.render_finalny(projekt, jakosc="l")
    assert wyjscie.exists()
    assert wyjscie.stat().st_size > 0


def test_render_finalny_odmawia_bez_akceptacji(projekt):
    llm = StubLLM([("a", "Jedna scena.")], psuj_pierwsza=False)
    script = stage_script.generuj(projekt, llm)
    for seg in script.segmenty:
        seg.status = "approved"
    projekt.save_script(script)
    stage_scenes.synchronizuj(projekt, script)

    with pytest.raises(RuntimeError, match="zatwierdzenia"):
        stage_scenes.render_finalny(projekt)

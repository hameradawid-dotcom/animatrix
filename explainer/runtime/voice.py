"""Wybór silnika mowy dla scen.

Sceny wołają `speech_service()` i nie wiedzą, czy pod spodem jest ElevenLabs
czy cisza. Przełącznik: zmienna środowiskowa EXPLAINER_TTS (elevenlabs|silent).

Cache audio jest wspólny dla całego projektu (`.cache/voiceover/`), a kluczem
jest hash tekstu + konfiguracji głosu. Dzięki temu poprawka jednej sceny nie
generuje ponownie audio pozostałych — i nie kosztuje ani jednego znaku.
"""

from __future__ import annotations

import contextlib
import os
import wave
from pathlib import Path

from manim_voiceover.helper import remove_bookmarks
from manim_voiceover.services.base import (
    SpeechService,
    initialize_speech_service,
    path_to_string,
)

DOMYSLNY_CACHE = ".cache/voiceover"
CZESTOTLIWOSC = 44100


def _zapisz_cisze(sciezka: Path, sekundy: float) -> None:
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    ramki = int(sekundy * CZESTOTLIWOSC)
    with contextlib.closing(wave.open(str(sciezka), "wb")) as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(CZESTOTLIWOSC)
        f.writeframes(b"\x00\x00" * ramki)


class SilentService(SpeechService):
    """Cisza o długości oszacowanej z tempa mowy.

    Nie dzwoni nigdzie, nie kosztuje nic. Używany do: renderów podglądowych,
    pętli samonaprawy kodu i pracy bez klucza ElevenLabs. `tracker.duration`
    działa normalnie, więc timing animacji jest realistyczny.
    """

    def __init__(self, znaki_na_sekunde: float = 14.5, minimum_s: float = 0.8, **kwargs: object) -> None:
        kwargs.setdefault("transcription_model", None)
        initialize_speech_service(self, kwargs, transcription_model=None)
        self.znaki_na_sekunde = znaki_na_sekunde
        self.minimum_s = minimum_s

    def generate_from_text(self, text, cache_dir=None, path=None, **kwargs):  # type: ignore[override]
        katalog = Path(cache_dir) if cache_dir is not None else Path(self.cache_dir)
        tekst = remove_bookmarks(text)
        input_data = {
            "input_text": tekst,
            "service": "silent",
            "config": {"cps": self.znaki_na_sekunde},
        }
        cached = self.get_cached_result(input_data, katalog)
        if cached is not None:
            return cached

        nazwa = self.get_audio_basename(input_data) + ".wav" if path is None else path_to_string(path)
        dlugosc = max(self.minimum_s, len(tekst) / max(self.znaki_na_sekunde, 1.0))
        _zapisz_cisze(katalog / nazwa, dlugosc)
        return {"input_text": text, "input_data": input_data, "original_audio": nazwa}


def _cache_dir() -> str:
    return os.environ.get("EXPLAINER_VOICE_CACHE", DOMYSLNY_CACHE)


def speech_service(cache_dir: str | None = None) -> SpeechService:
    """Zwraca skonfigurowany SpeechService. Wołaj w `construct()`:

        self.set_speech_service(speech_service(), create_subcaption=False)
    """
    katalog = cache_dir or _cache_dir()
    Path(katalog).mkdir(parents=True, exist_ok=True)

    provider = os.environ.get("EXPLAINER_TTS", "elevenlabs").strip().lower()
    if provider == "silent":
        return SilentService(
            znaki_na_sekunde=float(os.environ.get("EXPLAINER_SILENT_CPS", "14.5")),
            cache_dir=katalog,
        )

    klucz = os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("ELEVEN_API_KEY")
    if not klucz:
        raise RuntimeError(
            "Brak ELEVENLABS_API_KEY. Ustaw klucz w .env albo przełącz EXPLAINER_TTS=silent."
        )
    # manim-voiceover i biblioteka elevenlabs czytają wyłącznie ELEVEN_API_KEY.
    os.environ["ELEVEN_API_KEY"] = klucz

    from manim_voiceover.services.elevenlabs import ElevenLabsService

    return ElevenLabsService(
        voice_id=os.environ.get("ELEVENLABS_VOICE_ID") or None,
        model=os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"),
        transcription_model=None,
        cache_dir=katalog,
    )

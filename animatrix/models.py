from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

SegmentStatus = Literal["draft", "approved"]
SceneStatus = Literal["pending", "generated", "rendered", "approved", "failed"]

STAGES = ("script", "storyboard", "scene")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Uwaga(BaseModel):
    """Uwaga słowna użytkownika przy regeneracji. Historia trafia z powrotem do modelu."""

    etap: str
    tekst: str
    czas: str = Field(default_factory=_now)


class ScriptMeta(BaseModel):
    temat: str
    jezyk: str = "pl"
    docelowa_dlugosc_s: int = 90
    grupa_docelowa: str = ""
    ton: str = ""
    kluczowe_punkty: list[str] = Field(default_factory=list)
    motyw: str = "kh"
    # Preset kadru: "9:16" (TikTok, Reels), "4:5", "1:1", "16:9".
    format_wideo: str = "16:9"

    @field_validator("format_wideo", mode="before")
    @classmethod
    def _stare_nazwy_formatu(cls, v: object) -> object:
        """Projekty z pierwszej wersji mają "poziom"/"pion" — mapujemy je,
        żeby otwierały się bez ręcznej edycji YAML-a."""
        from animatrix.formaty import ALIASY

        return ALIASY.get(v, v) if isinstance(v, str) else v


class Segment(BaseModel):
    id: str
    narracja: str
    status: SegmentStatus = "draft"
    uwagi: list[Uwaga] = Field(default_factory=list)


class Script(BaseModel):
    meta: ScriptMeta
    segmenty: list[Segment] = Field(default_factory=list)

    def get(self, seg_id: str) -> Segment | None:
        return next((s for s in self.segmenty if s.id == seg_id), None)

    @property
    def approved(self) -> bool:
        return bool(self.segmenty) and all(s.status == "approved" for s in self.segmenty)


class StoryboardItem(BaseModel):
    id: str
    opis_wizualny: str
    obiekty: list[str] = Field(default_factory=list)
    animacje: list[str] = Field(default_factory=list)
    assety: list[str] = Field(default_factory=list)
    status: SegmentStatus = "draft"
    podglad: str | None = None
    uwagi: list[Uwaga] = Field(default_factory=list)


class Storyboard(BaseModel):
    segmenty: list[StoryboardItem] = Field(default_factory=list)

    def get(self, seg_id: str) -> StoryboardItem | None:
        return next((s for s in self.segmenty if s.id == seg_id), None)

    @property
    def approved(self) -> bool:
        return bool(self.segmenty) and all(s.status == "approved" for s in self.segmenty)


class SceneState(BaseModel):
    id: str
    klasa: str
    plik: str
    # Spec sceny (`sceny/sNN.yaml`). Brak = scena na surowym Pythonie z `plik`.
    spec: str | None = None
    # Odcisk specu z chwili ostatniego renderu — po nim widać, że podgląd
    # jest nieaktualny, zamiast zgadywać po dacie pliku.
    hash_renderu: str | None = None
    status: SceneStatus = "pending"
    proby_naprawy: int = 0
    ostatni_blad: str | None = None
    render_roboczy: str | None = None
    render_final: str | None = None
    uwagi: list[Uwaga] = Field(default_factory=list)


class Scenes(BaseModel):
    segmenty: list[SceneState] = Field(default_factory=list)

    def get(self, seg_id: str) -> SceneState | None:
        return next((s for s in self.segmenty if s.id == seg_id), None)

    @property
    def approved(self) -> bool:
        return bool(self.segmenty) and all(s.status == "approved" for s in self.segmenty)


class Costs(BaseModel):
    """Licznik kosztów per projekt. Znaki ElevenLabs liczone per segment,
    żeby edycja jednej sceny nie księgowała ponownie pozostałych."""

    elevenlabs_znaki_per_segment: dict[str, int] = Field(default_factory=dict)
    elevenlabs_znaki_historycznie: int = 0
    llm_wywolania: int = 0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0

    @property
    def elevenlabs_znaki(self) -> int:
        return sum(self.elevenlabs_znaki_per_segment.values())

    def zapisz_narracje(self, seg_id: str, tekst: str) -> None:
        nowe = len(tekst)
        stare = self.elevenlabs_znaki_per_segment.get(seg_id)
        if stare == nowe:
            return
        if stare is not None:
            self.elevenlabs_znaki_historycznie += stare
        self.elevenlabs_znaki_per_segment[seg_id] = nowe

    def zapisz_llm(self, input_tokens: int, output_tokens: int) -> None:
        self.llm_wywolania += 1
        self.llm_input_tokens += input_tokens
        self.llm_output_tokens += output_tokens


def scene_class_name(seg_id: str) -> str:
    """s01 -> Scena_S01. Klasa musi być poprawnym identyfikatorem Pythona."""
    return "Scena_" + "".join(ch for ch in seg_id.upper() if ch.isalnum())

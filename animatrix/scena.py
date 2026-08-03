"""Scena jako dane, nie jako kod.

Do tej pory scena była plikiem `.py` napisanym przez model — nie dało się jej
pokazać w formularzu ani zwalidować przed renderem. Teraz scena to spec:
`sceny/sNN.yaml` z nazwą szablonu i jego parametrami. Interfejs wyświetla je
jako pola, silnik zamienia w obiekty Manima, a walidator sprawdza kompozycję,
zanim ruszy render.

Furtka kodowa (`szablon: kod`) zostaje — żeby jedna nietypowa scena nie
wymuszała rozpychania katalogu szablonów.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

SZABLON_KOD = "kod"

# Kolory podajemy nazwami roli, nie hexem — dzięki temu przełączenie motywu
# `misja` → `kh` nie wymaga dotykania ani jednej sceny.
KOLORY = {
    "akcent": "ACCENT",
    "akcent_2": "ACCENT_2",
    "wyroznienie": "ACCENT_3",
    "alarm": "WARN",
    "sukces": "OK",
    "stonowany": "MUTED",
    "tekst": "FG",
    "tekst_2": "FG_2",
    "siatka": "SIATKA",
    "tlo_alt": "BG_ALT",
}

TOLERANCJA_TEMPA = 0.02


class Sekcja(BaseModel):
    """Nagłówek briefingu w lewym górnym rogu (`pasek_misji`)."""

    numer: int = 1
    etykieta: str = ""


class SceneSpec(BaseModel):
    id: str
    narracja: str = ""
    szablon: str
    parametry: dict[str, Any] = Field(default_factory=dict)
    # Udziały w `tracker.duration`. Puste = domyślne tempo szablonu.
    tempo: dict[str, float] = Field(default_factory=dict)
    sekcja: Sekcja | None = None
    # Elementy, którym wolno na siebie nachodzić (mapa pod podpisem itp.).
    moze_nachodzic: list[str] = Field(default_factory=list)

    @field_validator("tempo")
    @classmethod
    def _tempo_sumuje_sie(cls, v: dict[str, float]) -> dict[str, float]:
        if not v:
            return v
        suma = sum(v.values())
        if abs(suma - 1.0) > TOLERANCJA_TEMPA:
            raise ValueError(f"udziały tempa sumują się do {suma:.2f}, a mają do 1.0")
        if any(u <= 0 for u in v.values()):
            raise ValueError("każdy udział tempa musi być dodatni")
        return v

    @model_validator(mode="after")
    def _kod_wymaga_pliku(self) -> "SceneSpec":
        if self.szablon == SZABLON_KOD:
            brakuje = [k for k in ("plik", "klasa") if not self.parametry.get(k)]
            if brakuje:
                raise ValueError(
                    f"szablon 'kod' wymaga parametrów: {', '.join(brakuje)}"
                )
        return self

    @property
    def wlasny_kod(self) -> bool:
        return self.szablon == SZABLON_KOD

    def hash(self) -> str:
        """Odcisk specu — po nim widać, czy render jest nieaktualny."""
        tresc = yaml.safe_dump(
            self.model_dump(mode="json"), allow_unicode=True, sort_keys=True
        )
        return hashlib.sha256(tresc.encode("utf-8")).hexdigest()[:16]


def sciezka_specu(root: Path, seg_id: str) -> Path:
    return root / "sceny" / f"{seg_id}.yaml"


def wczytaj(sciezka: Path) -> SceneSpec:
    raw = yaml.safe_load(sciezka.read_text(encoding="utf-8")) or {}
    return SceneSpec.model_validate(raw)


def zapisz(spec: SceneSpec, sciezka: Path) -> None:
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    tmp = sciezka.with_suffix(sciezka.suffix + ".tmp")
    tmp.write_text(
        yaml.safe_dump(
            spec.model_dump(mode="json", exclude_none=True),
            allow_unicode=True,
            sort_keys=False,
            width=100,
        ),
        encoding="utf-8",
    )
    tmp.replace(sciezka)

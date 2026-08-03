"""Formaty wideo i strefy bezpieczne platform.

Jedno źródło prawdy dla proporcji kadru, rozdzielczości i obszaru, w którym
interfejs TikToka czy Instagrama nie zasłoni treści.
"""

from __future__ import annotations

from dataclasses import dataclass

DOMYSLNY = "16:9"

# Stare nazwy formatu z pierwszej wersji narzędzia. Trzymamy mapowanie, żeby
# istniejące projekty otwierały się bez ręcznej edycji YAML-a.
ALIASY = {"poziom": "16:9", "pion": "9:16"}


@dataclass(frozen=True)
class StrefaBezpieczna:
    """Margines w pikselach, w który nie wolno wchodzić treści.

    UWAGA: te liczby to PRZYBLIŻENIA. Każda aktualizacja aplikacji potrafi je
    zmienić, a TikTok i Instagram nie publikują ich jako kontraktu. Traktuj je
    jako punkt wyjścia i zweryfikuj na własnym telefonie przed serią publikacji.

    Ostatnia weryfikacja założeń: sierpień 2026.
    """

    gora: int = 0
    dol: int = 0
    lewo: int = 0
    prawo: int = 0
    zrodlo: str = ""


# Dół jest największy, bo mieszczą się tam opis, nazwa konta i pasek dźwięku;
# prawa krawędź to kolumna przycisków (polub, komentarz, udostępnij).
STREFY = {
    "tiktok": StrefaBezpieczna(
        gora=130, dol=480, lewo=40, prawo=120, zrodlo="przybliżenie, sierpień 2026"
    ),
    "reels": StrefaBezpieczna(
        gora=220, dol=420, lewo=40, prawo=120, zrodlo="przybliżenie, sierpień 2026"
    ),
    "feed": StrefaBezpieczna(gora=60, dol=60, lewo=40, prawo=40, zrodlo="zapas redakcyjny"),
    "youtube": StrefaBezpieczna(gora=40, dol=90, lewo=40, prawo=40, zrodlo="pasek sterowania"),
    "brak": StrefaBezpieczna(),
}


@dataclass(frozen=True)
class Format:
    nazwa: str
    szerokosc: int
    wysokosc: int
    fps: int
    strefa: str
    opis: str

    @property
    def proporcja(self) -> float:
        return self.szerokosc / self.wysokosc

    @property
    def pionowy(self) -> bool:
        return self.wysokosc > self.szerokosc

    def strefa_bezpieczna(self) -> StrefaBezpieczna:
        return STREFY.get(self.strefa, STREFY["brak"])


FORMATY = {
    "9:16": Format("9:16", 1080, 1920, 30, "tiktok", "TikTok, Reels, Shorts"),
    "4:5": Format("4:5", 1080, 1350, 30, "feed", "feed Instagrama"),
    "1:1": Format("1:1", 1080, 1080, 30, "feed", "kwadrat"),
    "16:9": Format("16:9", 1920, 1080, 30, "youtube", "YouTube, prezentacje"),
}

# Mnożnik rozdzielczości względem docelowej. Render roboczy ma być szybki,
# ale MUSI mieć tę samą proporcję — inaczej podgląd kłamie o kompozycji.
SKALA_JAKOSCI = {"l": 0.5, "m": 0.75, "h": 1.0, "k": 2.0}


class FormatError(ValueError):
    pass


def znormalizuj(nazwa: str | None) -> str:
    if not nazwa:
        return DOMYSLNY
    nazwa = nazwa.strip()
    nazwa = ALIASY.get(nazwa, nazwa)
    if nazwa not in FORMATY:
        raise FormatError(f"Nie znam formatu '{nazwa}'. Dostępne: {', '.join(FORMATY)}")
    return nazwa


def format_wideo(nazwa: str | None) -> Format:
    return FORMATY[znormalizuj(nazwa)]


def _parzysta(wartosc: float) -> int:
    """Kodery H.264 wymagają wymiarów podzielnych przez 2."""
    return max(2, int(round(wartosc / 2)) * 2)


def rozdzielczosc(nazwa: str | None, jakosc: str = "h") -> tuple[int, int, int]:
    fmt = format_wideo(nazwa)
    mnoznik = SKALA_JAKOSCI.get(jakosc, 1.0)
    return (
        _parzysta(fmt.szerokosc * mnoznik),
        _parzysta(fmt.wysokosc * mnoznik),
        fmt.fps,
    )


def opis_kadru(nazwa: str | None, wysokosc_jednostek: float = 8.0) -> str:
    """Zdanie do promptu systemowego — z REALNYMI wymiarami kadru.

    Wcześniej prompt miał zahardkodowane 16:9 nawet dla projektów pionowych,
    więc model dostawał błędne wymiary i budował kompozycje wychodzące poza kadr.
    """
    fmt = format_wideo(nazwa)
    szerokosc_j = wysokosc_jednostek * fmt.proporcja
    strefa = fmt.strefa_bezpieczna()
    tekst = (
        f"Kadr {fmt.nazwa} ({fmt.szerokosc}x{fmt.wysokosc} px) to "
        f"{szerokosc_j:.2f} jednostek szerokości na {wysokosc_jednostek:.0f} wysokości, "
        f"czyli x od {-szerokosc_j / 2:.2f} do {szerokosc_j / 2:.2f}, "
        f"y od {-wysokosc_jednostek / 2:.0f} do {wysokosc_jednostek / 2:.0f}."
    )
    if strefa.gora or strefa.dol:
        px_na_j = fmt.wysokosc / wysokosc_jednostek
        tekst += (
            f" Interfejs platformy zasłania {strefa.gora} px u góry i {strefa.dol} px u dołu, "
            f"czyli {strefa.gora / px_na_j:.2f} i {strefa.dol / px_na_j:.2f} jednostki — "
            "nie umieszczaj tam nic ważnego."
        )
    return tekst

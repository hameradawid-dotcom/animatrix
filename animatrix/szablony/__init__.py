"""Katalog szablonów scen.

Import tego pakietu NIE wciąga Manima — schematy parametrów są czystym
pydantikiem, żeby interfejs mógł zbudować z nich formularz bez renderowania
czegokolwiek. Manim pojawia się dopiero w `zbuduj()`, czyli w podprocesie renderu.
"""

from __future__ import annotations

from animatrix.szablony.baza import Beat, Kompozycja, Kontekst, Szablon, SzablonError
from animatrix.szablony.karty import KARTA_TYTULOWA
from animatrix.szablony.liczby import LICZNIK_HERO, POROWNANIE_LICZB
from animatrix.szablony.siatki import SIATKA_JEDNOSTEK, SIATKA_PROGU
from animatrix.szablony.wykresy import LAMANA, PASKI_PROCENTOWE, SCHODKI, SLUPKI

KATALOG: dict[str, Szablon] = {
    s.nazwa: s
    for s in (
        KARTA_TYTULOWA,
        LICZNIK_HERO,
        POROWNANIE_LICZB,
        SLUPKI,
        PASKI_PROCENTOWE,
        LAMANA,
        SCHODKI,
        SIATKA_JEDNOSTEK,
        SIATKA_PROGU,
    )
}


def szablon(nazwa: str) -> Szablon:
    if nazwa not in KATALOG:
        raise SzablonError(
            f"Nie znam szablonu '{nazwa}'. Dostępne: {', '.join(sorted(KATALOG))} "
            "(albo 'kod' dla własnej sceny w Pythonie)."
        )
    return KATALOG[nazwa]


__all__ = [
    "Beat",
    "KATALOG",
    "Kompozycja",
    "Kontekst",
    "Szablon",
    "SzablonError",
    "szablon",
]

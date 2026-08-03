"""Podział wklejonego scenariusza na segmenty.

Scenariusze powstają w Claude albo GPT i trafiają tu jako blok tekstu. Podział
jest DETERMINISTYCZNY — regex plus słownik polskich skrótów, żadnego modelu.
Powody: jest natychmiastowy, powtarzalny i nie kosztuje tokenów, a jedyne, co
robi, to cięcie na zdania i grupowanie ich w segmenty po 1–2 zdania.

Dobór szablonu do segmentu to osobna sprawa — tam model ma sens, bo wybiera
z katalogu. Tutaj nie ma czego zgadywać.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Skróty, po których kropka NIGDY nie kończy zdania — same z siebie zapowiadają
# ciąg dalszy („ok. 170 pkt", „dr Kowalski"). Bez nich liczba rozpada się na dwa
# segmenty w środku.
SKROTY_OTWARTE = {
    "np",
    "ok",
    "tzn",
    "tj",
    "m.in",
    "ur",
    "ul",
    "al",
    "dr",
    "prof",
    "hab",
    "inż",
    "mgr",
    "por",
    "zob",
    "wg",
    "ws",
    "im",
    "św",
}

# Skróty, które równie dobrze mogą kończyć zdanie: „321 tys." na końcu zdania
# wygląda identycznie jak „256 tys. osób" w środku. Rozstrzyga to, czy dalej
# zaczyna się nowe zdanie wielką literą.
SKROTY_JEDNOSTKOWE = {
    "tys",
    "mln",
    "mld",
    "proc",
    "pkt",
    "godz",
    "min",
    "r",
    "str",
    "nr",
    "poz",
    "art",
    "ust",
    "itd",
    "itp",
}

SKROTY = SKROTY_OTWARTE | SKROTY_JEDNOSTKOWE
WIELKA_LITERA = re.compile(r"^[\"„»(]*[A-ZĄĆĘŁŃÓŚŹŻ]")

KONIEC_ZDANIA = re.compile(r"(?<=[.!?…])\s+")
SKROT_NA_KONCU = re.compile(r"(?:^|\s)([\w.]+)\.$", re.UNICODE)
INICJAL = re.compile(r"\s[A-ZĄĆĘŁŃÓŚŹŻ]\.$")
LICZBA_NA_KONCU = re.compile(r"\d+\.$")

# Ile znaków narracji mieści się w sekundzie mowy. Tempo lektora liczone
# z realnych nagrań ElevenLabs po polsku.
ZNAKI_NA_SEKUNDE = 14.5

# Segment dłuższy niż to trwa ponad ~11 s — na TikToku to wieczność bez cięcia.
MAKS_ZNAKOW = 165
MIN_ZNAKOW = 40


@dataclass
class Kawalek:
    id: str
    narracja: str

    @property
    def znakow(self) -> int:
        return len(self.narracja)

    @property
    def sekundy(self) -> float:
        return self.znakow / ZNAKI_NA_SEKUNDE


def _koncowka_to_skrot(fragment: str, dalej: str = "") -> bool:
    fragment = fragment.rstrip()
    if INICJAL.search(fragment):
        return True
    if LICZBA_NA_KONCU.search(fragment):
        # „Próg wyniósł 149." kończy zdanie, „o godz. 18. rano" nie. Rozstrzyga
        # to samo co przy skrótach jednostkowych: co jest dalej.
        return not (dalej and WIELKA_LITERA.match(dalej))
    dopasowanie = SKROT_NA_KONCU.search(fragment)
    if not dopasowanie:
        return False
    slowo = dopasowanie.group(1).rstrip(".").lower()
    slowo = "".join(
        ch for ch in unicodedata.normalize("NFC", slowo) if ch.isalnum() or ch == "."
    )
    if slowo in SKROTY_JEDNOSTKOWE:
        return not (dalej and WIELKA_LITERA.match(dalej))
    return slowo in SKROTY_OTWARTE


def zdania(tekst: str) -> list[str]:
    """Tnie tekst na zdania, respektując polskie skróty i inicjały."""
    tekst = re.sub(r"[ \t]+", " ", tekst.strip())
    if not tekst:
        return []

    wynik: list[str] = []
    bufor = ""
    kawalki = KONIEC_ZDANIA.split(tekst)
    for i, kawalek in enumerate(kawalki):
        bufor = f"{bufor} {kawalek}".strip() if bufor else kawalek
        nastepny = kawalki[i + 1] if i + 1 < len(kawalki) else ""
        if _koncowka_to_skrot(bufor, nastepny):
            continue
        wynik.append(bufor)
        bufor = ""
    if bufor:
        wynik.append(bufor)
    return [z for z in (w.strip() for w in wynik) if z]


def _tnij_dlugie(zdanie: str, maks: int) -> list[str]:
    """Zdanie dłuższe niż limit dzielimy na przecinku albo myślniku.

    Nie tniemy w losowym miejscu — segment ma być zdaniem, nie urwanym kawałkiem.
    Jeśli nie ma na czym ciąć, zostawiamy jak jest i zgłosi to walidacja długości.
    """
    if len(zdanie) <= maks:
        return [zdanie]
    czesci = re.split(r"(?<=[,;—–])\s+", zdanie)
    if len(czesci) < 2:
        return [zdanie]

    wynik: list[str] = []
    bufor = ""
    for czesc in czesci:
        kandydat = f"{bufor} {czesc}".strip()
        if bufor and len(kandydat) > maks:
            wynik.append(bufor)
            bufor = czesc
        else:
            bufor = kandydat
    if bufor:
        wynik.append(bufor)
    return wynik


def podziel(
    tekst: str,
    *,
    maks_znakow: int = MAKS_ZNAKOW,
    min_znakow: int = MIN_ZNAKOW,
    prefiks: str = "s",
) -> list[Kawalek]:
    """Wklejony scenariusz → segmenty po 1–2 zdania.

    Puste linie w tekście są traktowane jako świadome granice segmentów —
    jeśli ktoś sformatował scenariusz akapitami, szanujemy jego podział.
    """
    akapity = [a for a in re.split(r"\n\s*\n", tekst) if a.strip()]
    segmenty: list[str] = []

    for akapit in akapity:
        bufor = ""
        for zdanie in zdania(akapit):
            for czesc in _tnij_dlugie(zdanie, maks_znakow):
                kandydat = f"{bufor} {czesc}".strip() if bufor else czesc
                # Dokładamy drugie zdanie tylko wtedy, gdy oba są krótkie —
                # segment to jedna myśl i jeden pomysł wizualny.
                if bufor and (len(kandydat) > maks_znakow or len(bufor) >= min_znakow):
                    segmenty.append(bufor)
                    bufor = czesc
                else:
                    bufor = kandydat
        if bufor:
            segmenty.append(bufor)

    return [Kawalek(id=f"{prefiks}{i + 1:02d}", narracja=t) for i, t in enumerate(segmenty)]


def przenumeruj(kawalki: list[Kawalek], *, prefiks: str = "s") -> list[Kawalek]:
    return [Kawalek(id=f"{prefiks}{i + 1:02d}", narracja=k.narracja) for i, k in enumerate(kawalki)]


def scal(kawalki: list[Kawalek], indeks: int, *, prefiks: str = "s") -> list[Kawalek]:
    """Łączy segment o podanym indeksie z następnym."""
    if not 0 <= indeks < len(kawalki) - 1:
        raise IndexError("Nie ma z czym scalić tego segmentu.")
    polaczony = Kawalek(
        id=kawalki[indeks].id,
        narracja=f"{kawalki[indeks].narracja} {kawalki[indeks + 1].narracja}".strip(),
    )
    nowe = kawalki[:indeks] + [polaczony] + kawalki[indeks + 2 :]
    return przenumeruj(nowe, prefiks=prefiks)


def rozdziel(kawalki: list[Kawalek], indeks: int, *, prefiks: str = "s") -> list[Kawalek]:
    """Dzieli segment na zdania — po jednym segmencie na zdanie."""
    if not 0 <= indeks < len(kawalki):
        raise IndexError("Nie ma takiego segmentu.")
    czesci = zdania(kawalki[indeks].narracja)
    if len(czesci) < 2:
        raise ValueError("Ten segment to jedno zdanie — nie ma go gdzie podzielić.")
    nowe = (
        kawalki[:indeks]
        + [Kawalek(id="", narracja=c) for c in czesci]
        + kawalki[indeks + 1 :]
    )
    return przenumeruj(nowe, prefiks=prefiks)


def dlugosc_s(kawalki: list[Kawalek]) -> float:
    return sum(k.sekundy for k in kawalki)

"""Bumper: hook otwierający, plansza tytułowa, zastrzeżenie na koniec."""

from __future__ import annotations

from pydantic import BaseModel

from animatrix.szablony.baza import Beat, Kompozycja, Kontekst, Szablon


class KartaParametry(BaseModel):
    eyebrow: str = ""
    tytul: str
    podpis: str = ""
    ramka: bool = True
    rozmiar_tytulu: int = 56
    kolor_ramki: str = "akcent"


def _karta_tytulowa(k: Kontekst, p: KartaParametry) -> Kompozycja:
    t = k.t

    czesci = []
    eyebrow = t.mono(p.eyebrow.upper(), color=t.ACCENT) if p.eyebrow else None
    if eyebrow is not None:
        czesci.append(eyebrow)

    naglowek = t.tytul(p.tytul, font_size=t.skaluj(p.rozmiar_tytulu))
    czesci.append(naglowek)

    podpis = t.podtytul(p.podpis) if p.podpis else None
    if podpis is not None:
        czesci.append(podpis)

    blok = t.VGroup(*czesci).arrange(t.DOWN, buff=t.sp(24))
    ramka = t.naroza(blok, kolor=k.kolor(p.kolor_ramki), margines=48) if p.ramka else None
    rdzen = t.VGroup(blok, ramka) if ramka is not None else blok

    beaty: list[Beat] = []
    if eyebrow is not None:
        beaty.append(Beat("eyebrow", 0.2, lambda s: [t.Write(eyebrow)]))
    beaty.append(Beat("tytul", 0.45, lambda s: [t.Write(naglowek)]))

    domkniecie = [a for a in (t.Create(ramka) if ramka is not None else None,) if a is not None]
    if podpis is not None:
        domkniecie.append(t.FadeIn(podpis))
    if domkniecie:
        beaty.append(Beat("domkniecie", 0.35, lambda s, a=domkniecie: a))

    return Kompozycja(rdzen=rdzen, beaty=beaty, kontrola={"karta": blok})


KARTA_TYTULOWA = Szablon(
    nazwa="karta_tytulowa",
    opis="Plansza z tytułem w narożnikach celownika — hook albo bumper.",
    Parametry=KartaParametry,
    zbuduj=_karta_tytulowa,
    pokrywa="otwarcie, tytuł odcinka",
    przyklad={
        "eyebrow": "// zadanie",
        "tytul": "Lekarski\n2027",
        "podpis": "PUM Szczecin",
        "ramka": True,
    },
)

"""Szablony, w których bohaterem jest liczba."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from animatrix.szablony.baza import Beat, Kompozycja, Kontekst, Szablon, SzablonError


class Pozycja(BaseModel):
    wartosc: float | str
    etykieta: str = ""
    kolor: str = "akcent"
    liczba_cyfr: int = 0
    sufiks: str = ""


class Podsumowanie(BaseModel):
    wartosc: float | str
    opis: str = ""
    kolor: str = "wyroznienie"
    liczba_cyfr: int = 1
    sufiks: str = ""


# --------------------------------------------------------------------------
# licznik_hero
# --------------------------------------------------------------------------
class LicznikHeroParametry(BaseModel):
    wartosc: float | str
    liczba_cyfr: int = 0
    sufiks: str = ""
    kolor: str = "wyroznienie"
    rozmiar: int = 110
    podpis: str = ""
    ramka: bool = False
    opis: str = ""
    zastrzezenie: str = ""


def _licznik_hero(k: Kontekst, p: LicznikHeroParametry) -> Kompozycja:
    t = k.t
    docelowa = float(k.wartosc(p.wartosc))
    kolor = k.kolor(p.kolor)

    tracker = t.ValueTracker(0)
    liczba = t.licznik(
        tracker,
        liczba_cyfr=p.liczba_cyfr,
        rozmiar=t.skaluj(p.rozmiar),
        kolor=kolor,
        sufiks=p.sufiks,
        docelowa=docelowa,
    )
    blok = t.VGroup(liczba)
    podpis = t.mono(p.podpis) if p.podpis else None
    if podpis is not None:
        blok = t.VGroup(liczba, podpis).arrange(t.DOWN, buff=t.sp(12))

    ramka = t.naroza(blok, kolor=kolor, margines=48) if p.ramka else None
    rdzen = t.VGroup(blok, ramka) if ramka is not None else blok

    opis = t.body(p.opis, font_size=t.skaluj(28)) if p.opis else None
    zastrzezenie = None
    if p.zastrzezenie:
        zastrzezenie = t.mono(p.zastrzezenie, color=t.MUTED).scale(0.62)

    def takt_liczba(scene):
        scene.add(liczba)
        anim = [tracker.animate.set_value(docelowa)]
        if podpis is not None:
            anim.append(t.FadeIn(podpis))
        return anim

    beaty = [Beat("liczba", 0.42, takt_liczba, rate_func=t.rate_functions.ease_out_cubic)]
    if ramka is not None:
        beaty.append(Beat("ramka", 0.16, lambda s: [t.Create(ramka)]))
    if opis is not None:
        beaty.append(Beat("opis", 0.22, lambda s: [t.FadeIn(opis, shift=t.UP * t.sp(12))]))
    if zastrzezenie is not None:
        beaty.append(Beat("zastrzezenie", 0.20, lambda s: [t.FadeIn(zastrzezenie)]))

    return Kompozycja(
        rdzen=rdzen,
        pod=opis,
        stopka=zastrzezenie,
        beaty=beaty,
        kontrola={"liczba": blok, "opis": opis, "zastrzezenie": zastrzezenie},
    )


# --------------------------------------------------------------------------
# porownanie_liczb
# --------------------------------------------------------------------------
class PorownanieParametry(BaseModel):
    pozycje: list[Pozycja] = Field(min_length=2, max_length=3)
    separator: bool = True
    rozmiar: int = 96
    podsumowanie: Podsumowanie | None = None


def _porownanie_liczb(k: Kontekst, p: PorownanieParametry) -> Kompozycja:
    t = k.t
    bezpieczny = k.kadr.bezpieczny()

    trackery, bloki, liczby = [], [], []
    for poz in p.pozycje:
        docelowa = float(k.wartosc(poz.wartosc))
        tracker = t.ValueTracker(0)
        liczba = t.licznik(
            tracker,
            liczba_cyfr=poz.liczba_cyfr,
            rozmiar=t.skaluj(p.rozmiar),
            kolor=k.kolor(poz.kolor),
            sufiks=poz.sufiks,
            docelowa=docelowa,
        )
        podpis = t.mono(poz.etykieta.upper()) if poz.etykieta else None
        blok = t.VGroup(liczba, podpis).arrange(t.DOWN, buff=t.sp(8)) if podpis else t.VGroup(liczba)
        trackery.append((tracker, docelowa, podpis))
        bloki.append(blok)
        liczby.append(liczba)

    czesci: list[Any] = []
    separatory = []
    for i, blok in enumerate(bloki):
        if i and p.separator:
            kreska = t.linia(bezpieczny.szerokosc * 0.55)
            separatory.append(kreska)
            czesci.append(kreska)
        czesci.append(blok)
    rdzen = t.VGroup(*czesci).arrange(t.DOWN, buff=t.sp(24))

    pod = None
    t_pods = None
    if p.podsumowanie is not None:
        cel = float(k.wartosc(p.podsumowanie.wartosc))
        t_pods = t.ValueTracker(0)
        wartosc = t.licznik(
            t_pods,
            liczba_cyfr=p.podsumowanie.liczba_cyfr,
            rozmiar=t.skaluj(72),
            kolor=k.kolor(p.podsumowanie.kolor),
            sufiks=p.podsumowanie.sufiks,
            docelowa=cel,
        )
        opis = t.body(p.podsumowanie.opis, font_size=t.skaluj(24))
        pod = t.VGroup(wartosc, opis).arrange(t.DOWN, buff=t.sp(16))
        pods = (t_pods, cel, wartosc, opis)

    beaty: list[Beat] = []
    for i, (tracker, docelowa, podpis) in enumerate(trackery):

        def takt(scene, tracker=tracker, docelowa=docelowa, podpis=podpis, i=i):
            scene.add(liczby[i])
            anim = [tracker.animate.set_value(docelowa)]
            if podpis is not None:
                anim.append(t.FadeIn(podpis))
            if i and separatory:
                anim.append(t.Create(separatory[i - 1]))
            return anim

        beaty.append(
            Beat(f"liczba_{i + 1}", 0.30, takt, rate_func=t.rate_functions.ease_out_cubic)
        )

    if p.podsumowanie is not None:

        def takt_pods(scene, pods=pods):
            tr, cel, wartosc, opis = pods
            scene.add(wartosc)
            return [tr.animate.set_value(cel), t.FadeIn(opis)]

        beaty.append(
            Beat("podsumowanie", 0.28, takt_pods, rate_func=t.rate_functions.ease_out_cubic)
        )
        beaty.append(
            Beat(
                "akcent",
                0.12,
                lambda s: [t.Indicate(pods[2], color=pods[2].get_color(), scale_factor=1.12)],
            )
        )

    kontrola = {f"blok_{i + 1}": b for i, b in enumerate(bloki)}
    if pod is not None:
        kontrola["podsumowanie"] = pod
    return Kompozycja(rdzen=rdzen, pod=pod, beaty=beaty, kontrola=kontrola)


LICZNIK_HERO = Szablon(
    nazwa="licznik_hero",
    opis="Jedna wielka liczba z podpisem — puenta albo hook.",
    Parametry=LicznikHeroParametry,
    zbuduj=_licznik_hero,
    pokrywa="cel, wynik, pojedyncza wartość",
    przyklad={
        "wartosc": 170,
        "podpis": "/ 200 pkt",
        "ramka": True,
        "opis": "85%\nz chemii i biologii",
        "zastrzezenie": "szacunek",
    },
)

POROWNANIE_LICZB = Szablon(
    nazwa="porownanie_liczb",
    opis="Dwie lub trzy liczby jedna pod drugą plus opcjonalne podsumowanie.",
    Parametry=PorownanieParametry,
    zbuduj=_porownanie_liczb,
    pokrywa="miejsca vs kandydaci, przed vs po",
    przyklad={
        "pozycje": [
            {"wartosc": 255, "etykieta": "miejsc", "kolor": "akcent"},
            {"wartosc": 5202, "etykieta": "kandydatów", "kolor": "alarm"},
        ],
        "podsumowanie": {"wartosc": 20.4, "opis": "na jedno miejsce", "liczba_cyfr": 1},
    },
)

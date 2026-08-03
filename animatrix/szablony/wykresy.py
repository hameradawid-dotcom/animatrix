"""Szablony danych w czasie: słupki, paski, łamana, schodki."""

from __future__ import annotations

from pydantic import BaseModel, Field

from animatrix.szablony.baza import Beat, Kompozycja, Kontekst, Szablon

SZEROKOSC_RDZENIA = 0.94
WYSOKOSC_RDZENIA = 0.42


def _obszar(k: Kontekst) -> tuple[float, float]:
    b = k.kadr.bezpieczny()
    return b.szerokosc * SZEROKOSC_RDZENIA, b.wysokosc * WYSOKOSC_RDZENIA


def _zmiesc(mobject, maks_szerokosc: float) -> None:
    if mobject.width > maks_szerokosc > 0:
        mobject.scale(maks_szerokosc / mobject.width)


# --------------------------------------------------------------------------
# slupki
# --------------------------------------------------------------------------
class Slupek(BaseModel):
    etykieta: str = ""
    wartosc: float | str
    kolor: str = "akcent"
    przygaszony: bool = False
    adnotacja: str = ""


class SlupkiParametry(BaseModel):
    pozycje: list[Slupek] = Field(min_length=2)
    jednostka: str = ""
    puenta: str = ""
    format_wartosci: str = "{:g}"


def _slupki(k: Kontekst, p: SlupkiParametry) -> Kompozycja:
    t = k.t
    szer, wys = _obszar(k)
    n = len(p.pozycje)
    szer_slupka = szer / (n * 1.55)
    odstep = szer_slupka * 0.55

    wartosci = [float(k.wartosc(poz.wartosc)) for poz in p.pozycje]
    maks = max(wartosci) or 1.0

    podstawa = t.Line(t.LEFT * szer / 2, t.RIGHT * szer / 2, color=t.SIATKA, stroke_width=2)
    calosc = n * szer_slupka + (n - 1) * odstep
    start = -calosc / 2 + szer_slupka / 2

    slupki, opisy = t.VGroup(), t.VGroup()
    for i, (poz, wartosc) in enumerate(zip(p.pozycje, wartosci)):
        kolor = k.kolor(poz.kolor)
        slupek = t.Rectangle(
            width=szer_slupka,
            height=max(wartosc / maks * wys, 0.02),
            fill_color=kolor,
            fill_opacity=0.45 if poz.przygaszony else 1.0,
            stroke_width=0,
        )
        slupek.align_to(podstawa, t.DOWN).set_x(start + i * (szer_slupka + odstep))
        slupki.add(slupek)

        nad = []
        if poz.adnotacja:
            nad.append(t.mono(poz.adnotacja.upper(), color=t.MUTED))
        nad.append(t.body(p.format_wartosci.format(wartosc), color=kolor, font_size=t.skaluj(24)))
        stos_nad = t.VGroup(*nad).arrange(t.DOWN, buff=t.sp(4))
        _zmiesc(stos_nad, szer_slupka + odstep)
        stos_nad.next_to(slupek, t.UP, buff=t.sp(8))

        pod_slupkiem = t.mono(poz.etykieta)
        _zmiesc(pod_slupkiem, szer_slupka + odstep)
        pod_slupkiem.next_to(podstawa, t.DOWN, buff=t.sp(12)).set_x(slupek.get_x())

        opisy.add(t.VGroup(stos_nad, pod_slupkiem))

    rdzen = t.VGroup(podstawa, slupki, opisy)

    dolne = []
    if p.jednostka:
        dolne.append(t.etykieta(p.jednostka))
    if p.puenta:
        dolne.append(t.body(p.puenta, color=t.ACCENT_3, font_size=t.skaluj(26)))
    pod = t.VGroup(*dolne).arrange(t.DOWN, buff=t.sp(16)) if dolne else None

    beaty = [
        Beat("os", 0.14, lambda s: [t.Create(podstawa)]),
        Beat(
            "slupki",
            0.44,
            lambda s: [
                t.LaggedStart(*[t.GrowFromEdge(x, t.DOWN) for x in slupki], lag_ratio=0.35)
            ],
        ),
        Beat("opisy", 0.24, lambda s: [t.FadeIn(opisy)]),
    ]
    if pod is not None:
        beaty.append(Beat("puenta", 0.18, lambda s: [t.FadeIn(pod, shift=t.UP * t.sp(12))]))

    return Kompozycja(
        rdzen=rdzen,
        pod=pod,
        beaty=beaty,
        kontrola={"wykres": rdzen, "podpis": pod},
    )


# --------------------------------------------------------------------------
# paski_procentowe
# --------------------------------------------------------------------------
class Pasek(BaseModel):
    etykieta: str
    wartosc: float | str
    kolor: str = "akcent"
    sufiks: str = "%"


class PaskiParametry(BaseModel):
    pozycje: list[Pasek] = Field(min_length=1)
    puenta: str = ""
    format_wartosci: str = "+{:.0f}"


def _paski_procentowe(k: Kontekst, p: PaskiParametry) -> Kompozycja:
    t = k.t
    szer, _ = _obszar(k)
    wartosci = [float(k.wartosc(poz.wartosc)) for poz in p.pozycje]
    maks = max(wartosci) or 1.0

    wiersze, wypelnienia = t.VGroup(), []
    for poz, wartosc in zip(p.pozycje, wartosci):
        kolor = k.kolor(poz.kolor)
        podpis = t.body(poz.etykieta, font_size=t.skaluj(24), color=t.FG)
        liczba = t.body(
            p.format_wartosci.format(wartosc) + poz.sufiks, color=kolor, font_size=t.skaluj(34)
        )
        naglowek = t.VGroup(podpis, liczba).arrange(t.RIGHT, buff=t.sp(24))
        _zmiesc(naglowek, szer)

        tor = t.Line(t.LEFT * szer / 2, t.RIGHT * szer / 2, color=t.SIATKA, stroke_width=2)
        wypelnienie = t.Line(
            tor.get_start(),
            tor.get_start() + t.RIGHT * szer * (wartosc / maks),
            color=kolor,
            stroke_width=16,
        )
        wypelnienia.append(wypelnienie)
        wiersz = t.VGroup(naglowek, t.VGroup(tor, wypelnienie)).arrange(t.DOWN, buff=t.sp(16))
        wiersze.add(wiersz)

    rdzen = wiersze.arrange(t.DOWN, buff=t.sp(48))
    pod = t.body(p.puenta, color=t.ACCENT_3, font_size=t.skaluj(28)) if p.puenta else None

    beaty: list[Beat] = [
        Beat(
            "tory",
            0.20,
            lambda s: [t.FadeIn(w[0]) for w in wiersze] + [t.Create(w[1][0]) for w in wiersze],
        )
    ]
    for i, wypelnienie in enumerate(wypelnienia):
        beaty.append(
            Beat(
                f"pasek_{i + 1}",
                0.28,
                lambda s, w=wypelnienie: [t.Create(w)],
                rate_func=t.rate_functions.ease_out_cubic,
            )
        )
    if pod is not None:
        beaty.append(Beat("puenta", 0.18, lambda s: [t.FadeIn(pod, shift=t.UP * t.sp(12))]))

    return Kompozycja(rdzen=rdzen, pod=pod, beaty=beaty, kontrola={"paski": rdzen, "puenta": pod})


# --------------------------------------------------------------------------
# lamana
# --------------------------------------------------------------------------
class Punkt(BaseModel):
    etykieta: str = ""
    wartosc: float | str


class LamanaParametry(BaseModel):
    punkty: list[Punkt] = Field(min_length=2)
    kolor: str = "akcent"
    wyroznij: str = "min"  # min | max | brak
    kolor_wyroznienia: str = "alarm"
    puenta: str = ""


def _lamana(k: Kontekst, p: LamanaParametry) -> Kompozycja:
    t = k.t
    szer, wys = _obszar(k)
    wartosci = [float(k.wartosc(pt.wartosc)) for pt in p.punkty]
    lo, hi = min(wartosci), max(wartosci)
    rozpietosc = (hi - lo) or 1.0
    kolor = k.kolor(p.kolor)
    kolor_w = k.kolor(p.kolor_wyroznienia)

    if p.wyroznij == "min":
        wyroznik = min(range(len(wartosci)), key=lambda i: wartosci[i])
    elif p.wyroznij == "max":
        wyroznik = max(range(len(wartosci)), key=lambda i: wartosci[i])
    else:
        wyroznik = -1

    os_x = t.Line(t.LEFT * szer / 2, t.RIGHT * szer / 2, color=t.SIATKA, stroke_width=2)
    krok_x = szer / max(len(wartosci) - 1, 1) * 0.86
    # Najniższy punkt musi mieć nad osią zapas na własną etykietę — inaczej
    # opis dołka ląduje dokładnie na podpisach lat.
    baza_y = os_x.get_y() + t.sp(64)

    wezly = []
    for i, wartosc in enumerate(wartosci):
        x = -krok_x * (len(wartosci) - 1) / 2 + i * krok_x
        y = baza_y + (wartosc - lo) / rozpietosc * wys
        wezly.append(t.np.array([x, y, 0.0]))

    lamana = t.VMobject(color=kolor, stroke_width=6).set_points_as_corners(wezly)
    kropki = t.VGroup(
        *[
            t.Dot(w, radius=0.09, color=kolor_w if i == wyroznik else kolor)
            for i, w in enumerate(wezly)
        ]
    )

    etykiety, wartosci_txt = t.VGroup(), t.VGroup()
    for i, (wartosc, wezel) in enumerate(zip(wartosci, wezly)):
        if p.punkty[i].etykieta:
            podpis = t.mono(p.punkty[i].etykieta)
            _zmiesc(podpis, krok_x)
            podpis.move_to([wezel[0], os_x.get_y() - t.sp(24), 0.0])
            etykiety.add(podpis)

        # Etykieta idzie na ZEWNĄTRZ załamania: nad wierzchołkiem, pod dołkiem.
        # Bez tej reguły napisy siadają na łamanej.
        sasiedzi = [wartosci[j] for j in (i - 1, i + 1) if 0 <= j < len(wartosci)]
        w_gore = wartosc >= max(sasiedzi)
        txt = t.body(
            f"{wartosc:g}",
            color=kolor_w if i == wyroznik else kolor,
            font_size=t.skaluj(30),
        )
        _zmiesc(txt, krok_x)
        if not w_gore and wezel[1] - t.sp(32) - txt.height < os_x.get_y():
            # Pod dołkiem nie ma już miejsca nad osią — wracamy nad punkt.
            w_gore = True
        odsun = t.sp(32) if w_gore else -t.sp(32)
        txt.move_to([wezel[0], wezel[1] + odsun + (txt.height / 2) * (1 if w_gore else -1), 0.0])
        wartosci_txt.add(txt)

    rdzen = t.VGroup(os_x, lamana, kropki, etykiety, wartosci_txt)
    pod = t.body(p.puenta, color=kolor_w, font_size=t.skaluj(26)) if p.puenta else None

    beaty = [
        Beat("os", 0.18, lambda s: [t.Create(os_x), t.FadeIn(etykiety)]),
        Beat("lamana", 0.34, lambda s: [t.Create(lamana)]),
        Beat(
            "punkty",
            0.26,
            lambda s: [
                t.LaggedStart(*[t.GrowFromCenter(x) for x in kropki], lag_ratio=0.3),
                t.FadeIn(wartosci_txt),
            ],
        ),
    ]
    if pod is not None or wyroznik >= 0:
        def domkniecie(scene):
            anim = []
            if pod is not None:
                anim.append(t.FadeIn(pod, shift=t.UP * t.sp(12)))
            if wyroznik >= 0:
                anim.append(t.Indicate(kropki[wyroznik], color=kolor_w, scale_factor=1.5))
            return anim

        beaty.append(Beat("wyroznienie", 0.22, domkniecie))

    return Kompozycja(rdzen=rdzen, pod=pod, beaty=beaty, kontrola={"wykres": rdzen, "puenta": pod})


# --------------------------------------------------------------------------
# schodki
# --------------------------------------------------------------------------
class Stopien(BaseModel):
    etykieta: str
    wartosc: float | str
    kolor: str = "akcent"


class SchodkiParametry(BaseModel):
    wiersze: list[Stopien] = Field(min_length=2)
    przesuniecie: float = 0.35
    podsumowanie: Stopien | None = None
    etykieta_podsumowania: str = ""
    ramka_podsumowania: bool = True


def _schodki(k: Kontekst, p: SchodkiParametry) -> Kompozycja:
    t = k.t
    szer, _ = _obszar(k)

    schodki = t.VGroup()
    for i, w in enumerate(p.wiersze):
        kolor = k.kolor(w.kolor)
        opis = t.mono(w.etykieta.upper())
        wartosc = t.body(f"{float(k.wartosc(w.wartosc)):g}", color=kolor, font_size=t.skaluj(40))
        wiersz = t.VGroup(opis, wartosc).arrange(t.RIGHT, buff=t.sp(32))
        _zmiesc(wiersz, szer * 0.7)
        schodki.add(wiersz)

    schodki.arrange(t.DOWN, buff=t.sp(32))
    for i, wiersz in enumerate(schodki):
        wiersz.shift(t.RIGHT * (p.przesuniecie * (len(schodki) - 1) / 2 - i * p.przesuniecie))
    _zmiesc(schodki, szer)

    pod = None
    ramka = None
    if p.podsumowanie is not None:
        kolor = k.kolor(p.podsumowanie.kolor)
        blok = t.VGroup(
            t.mono(
                (p.etykieta_podsumowania or p.podsumowanie.etykieta).upper(),
                color=kolor,
            ),
            t.body(
                f"{float(k.wartosc(p.podsumowanie.wartosc)):g}",
                color=kolor,
                font_size=t.skaluj(40),
            ),
        ).arrange(t.DOWN, buff=t.sp(12))
        if p.ramka_podsumowania:
            ramka = t.naroza(blok, kolor=kolor, margines=32, dlugosc=0.22)
            pod = t.VGroup(blok, ramka)
        else:
            pod = blok

    beaty = [
        Beat(
            "wiersze",
            0.62,
            lambda s: [
                t.LaggedStart(
                    *[t.FadeIn(w, shift=t.DOWN * t.sp(16)) for w in schodki], lag_ratio=0.45
                )
            ],
        )
    ]
    if pod is not None:
        beaty.append(Beat("podsumowanie", 0.38, lambda s: [t.FadeIn(pod)]))

    return Kompozycja(
        rdzen=schodki, pod=pod, beaty=beaty, kontrola={"schodki": schodki, "podsumowanie": pod}
    )


SLUPKI = Szablon(
    nazwa="slupki",
    opis="Wykres słupkowy z wartościami, etykietami i adnotacją nad wybranym słupkiem.",
    Parametry=SlupkiParametry,
    zbuduj=_slupki,
    pokrywa="liczebność roczników, średnie wyniki",
    przyklad={
        "pozycje": [
            {"etykieta": "2025", "wartosc": 256},
            {"etykieta": "2026", "wartosc": 321},
            {"etykieta": "2027", "wartosc": 386, "kolor": "wyroznienie", "adnotacja": "prognoza"},
        ],
        "jednostka": "tysięcy maturzystów",
    },
)

PASKI_PROCENTOWE = Szablon(
    nazwa="paski_procentowe",
    opis="Poziome paski porównawcze — „nożyce” dwóch wielkości.",
    Parametry=PaskiParametry,
    zbuduj=_paski_procentowe,
    pokrywa="wzrost miejsc vs wzrost kandydatów",
    przyklad={
        "pozycje": [
            {"etykieta": "miejsca", "wartosc": 1.9, "kolor": "stonowany"},
            {"etykieta": "kandydaci", "wartosc": 20.2, "kolor": "alarm"},
        ],
        "puenta": "dziesięć razy\nszybciej",
    },
)

LAMANA = Szablon(
    nazwa="lamana",
    opis="Trend w czasie z automatycznym omijaniem etykiet.",
    Parametry=LamanaParametry,
    zbuduj=_lamana,
    pokrywa="progi punktowe rok po roku",
    przyklad={
        "punkty": [
            {"etykieta": "2023", "wartosc": 158},
            {"etykieta": "2024", "wartosc": 143},
            {"etykieta": "2025", "wartosc": 149},
        ],
        "puenta": "nie rośnie\nrówno",
    },
)

SCHODKI = Szablon(
    nazwa="schodki",
    opis="Lista rankingowa schodząca w dół plus podsumowanie w ramce.",
    Parametry=SchodkiParametry,
    zbuduj=_schodki,
    pokrywa="kolejne listy rekrutacyjne",
    przyklad={
        "wiersze": [
            {"etykieta": "lista 1", "wartosc": 175},
            {"etykieta": "lista 2", "wartosc": 166},
            {"etykieta": "lista 3", "wartosc": 163},
        ],
        "podsumowanie": {"etykieta": "próg końcowy", "wartosc": 159, "kolor": "wyroznienie"},
    },
)

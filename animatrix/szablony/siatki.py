"""Siatki jednostek: „ile to jest” pokazane policzalnie, nie opisowo."""

from __future__ import annotations

from pydantic import BaseModel, Field

from animatrix.szablony.baza import Beat, Kompozycja, Kontekst, Szablon

SZEROKOSC_RDZENIA = 0.92
WYSOKOSC_RDZENIA = 0.44


def _bok_komorki(k: Kontekst, kolumny: int, wiersze: int, odstep: float) -> float:
    b = k.kadr.bezpieczny()
    z_szerokosci = (b.szerokosc * SZEROKOSC_RDZENIA - (kolumny - 1) * odstep) / kolumny
    z_wysokosci = (b.wysokosc * WYSOKOSC_RDZENIA - (wiersze - 1) * odstep) / wiersze
    return max(min(z_szerokosci, z_wysokosci), 0.04)


class Etap(BaseModel):
    od: int = 0
    ile: int = 1
    kolor: str = "akcent"
    kaskada: bool = False


class LicznikBloku(BaseModel):
    etykieta: str = ""
    od: float | str = 0
    do: float | str
    liczba_cyfr: int = 0
    sufiks: str = ""
    kolor: str = "akcent"
    rozmiar: int = 56
    # Po którym etapie wypełnienia licznik ma dojechać do wartości docelowej.
    po_etapie: int = 0


class SiatkaParametry(BaseModel):
    ilosc: int = Field(ge=1, le=400)
    kolumny: int = Field(default=10, ge=1, le=40)
    ksztalt: str = "kwadrat"  # kwadrat | kropka
    podpis: str = ""
    etapy: list[Etap] = Field(default_factory=list)
    licznik: LicznikBloku | None = None
    licznik_nad: bool = False
    puenta: str = ""
    rownanie: list[str] = Field(default_factory=list)


def _siatka_jednostek(k: Kontekst, p: SiatkaParametry) -> Kompozycja:
    t = k.t
    wiersze = -(-p.ilosc // p.kolumny)
    odstep = t.sp(12)
    bok = _bok_komorki(k, p.kolumny, wiersze, odstep)

    def komorka():
        if p.ksztalt == "kropka":
            return t.Dot(radius=bok / 2.4, color=t.MUTED, fill_opacity=0.55)
        return t.Square(
            side_length=bok, stroke_width=1.2, stroke_color=t.SIATKA, fill_opacity=0
        )

    siatka = t.VGroup(*[komorka() for _ in range(p.ilosc)])
    siatka.arrange_in_grid(rows=wiersze, cols=p.kolumny, buff=odstep)

    podpis = t.body(p.podpis, font_size=t.skaluj(24)) if p.podpis else None

    blok_licznika = None
    tracker = None
    if p.licznik is not None:
        kolor = k.kolor(p.licznik.kolor)
        start = float(k.wartosc(p.licznik.od))
        tracker = t.ValueTracker(start)
        liczba = t.licznik(
            tracker,
            liczba_cyfr=p.licznik.liczba_cyfr,
            rozmiar=t.skaluj(p.licznik.rozmiar),
            kolor=kolor,
            sufiks=p.licznik.sufiks,
            docelowa=start,
        )
        czesci = [liczba]
        if p.licznik.etykieta:
            czesci = [t.mono(p.licznik.etykieta.upper()), liczba]
        blok_licznika = t.VGroup(*czesci).arrange(t.DOWN, buff=t.sp(12))

    dolne = []
    if blok_licznika is not None and not p.licznik_nad:
        dolne.append(blok_licznika)
    if p.rownanie:
        wiersze_rownania = [
            t.body(
                tekst,
                font_size=t.skaluj(28),
                color=t.ACCENT_3 if i == len(p.rownanie) - 1 else t.FG,
            )
            for i, tekst in enumerate(p.rownanie)
        ]
        dolne.append(t.VGroup(*wiersze_rownania).arrange(t.DOWN, buff=t.sp(12)))
    if p.puenta:
        dolne.append(t.body(p.puenta, color=t.ACCENT_3, font_size=t.skaluj(28)))
    pod = t.VGroup(*dolne).arrange(t.DOWN, buff=t.sp(24)) if dolne else None

    nad_czesci = [x for x in (podpis, blok_licznika if p.licznik_nad else None) if x is not None]
    nad = t.VGroup(*nad_czesci).arrange(t.DOWN, buff=t.sp(16)) if nad_czesci else None

    def wypelnij(etap: Etap):
        kolor = k.kolor(etap.kolor)
        cele = [
            siatka[i]
            for i in range(etap.od, min(etap.od + etap.ile, len(siatka)))
        ]
        return [
            komorka.animate.set_fill(kolor, opacity=1.0).set_stroke(kolor) for komorka in cele
        ], kolor

    beaty: list[Beat] = []
    if nad is not None:
        beaty.append(Beat("naglowek", 0.14, lambda s: [t.FadeIn(nad)]))

    def takt_siatka(scene):
        if tracker is not None:
            scene.add(blok_licznika)
        return [t.LaggedStart(*[t.FadeIn(x) for x in siatka], lag_ratio=0.008)]

    beaty.append(Beat("siatka", 0.30, takt_siatka))

    for i, etap in enumerate(p.etapy):

        def takt(scene, etap=etap, i=i):
            anim, _ = wypelnij(etap)
            if etap.kaskada:
                anim = [t.LaggedStart(*anim, lag_ratio=0.35)]
            if (
                p.licznik is not None
                and tracker is not None
                and p.licznik.po_etapie == i
            ):
                anim.append(tracker.animate.set_value(float(k.wartosc(p.licznik.do))))
            return anim

        beaty.append(Beat(f"etap_{i + 1}", 0.22, takt))

    if pod is not None:
        beaty.append(Beat("puenta", 0.20, lambda s: [t.FadeIn(pod, shift=t.UP * t.sp(12))]))

    return Kompozycja(
        rdzen=siatka,
        nad=nad,
        pod=pod,
        beaty=beaty,
        kontrola={"siatka": siatka, "nad": nad, "pod": pod},
    )


# --------------------------------------------------------------------------
# siatka_progu
# --------------------------------------------------------------------------
class SiatkaProguParametry(BaseModel):
    kolumny: int = Field(default=9, ge=2, le=30)
    wiersze: int = Field(default=11, ge=2, le=30)
    prog_od: float = 2.5
    prog_do: float = 1.5
    etykieta_progu: str = "próg"
    kolor_przyjetych: str = "akcent"
    kolor_odrzuconych: str = "alarm"
    kolor_progu: str = "wyroznienie"
    puenta: str = ""


def _siatka_progu(k: Kontekst, p: SiatkaProguParametry) -> Kompozycja:
    t = k.t
    odstep = t.sp(24)
    bok = _bok_komorki(k, p.kolumny, p.wiersze, odstep)

    kropki = t.VGroup(
        *[
            t.Dot(radius=bok / 2.6, color=t.MUTED, fill_opacity=0.55)
            for _ in range(p.kolumny * p.wiersze)
        ]
    )
    kropki.arrange_in_grid(rows=p.wiersze, cols=p.kolumny, buff=odstep)

    kolor_progu = k.kolor(p.kolor_progu)
    kolor_ok = k.kolor(p.kolor_przyjetych)
    kolor_nie = k.kolor(p.kolor_odrzuconych)

    prog = t.Line(
        kropki.get_left() + t.LEFT * t.sp(24),
        kropki.get_right() + t.RIGHT * t.sp(24),
        color=kolor_progu,
        stroke_width=4,
    )
    # Próg musi leżeć MIĘDZY wierszami, nie nad bounding boxem siatki —
    # inaczej po jednej ze stron nie ma ani jednej kropki. Pozycję liczymy
    # ZA KAŻDYM RAZEM na żywo, bo składacz kadru przesuwa i skaluje całą grupę
    # już po zbudowaniu sceny — zapamiętany y byłby wtedy nieaktualny.
    def y_progu(ile_wierszy: float) -> float:
        krok = kropki[0].get_y() - kropki[p.kolumny].get_y()
        return kropki[0].get_y() - krok * ile_wierszy

    prog.set_y(y_progu(p.prog_od))

    # Etykieta idzie OBOK linii, nie nad nią: nad linią siada na kropkach,
    # bo próg z definicji leży w środku siatki.
    opis = t.mono(p.etykieta_progu.upper(), color=kolor_progu)
    opis.next_to(prog, t.RIGHT, buff=t.sp(8))

    rdzen = t.VGroup(kropki, prog, opis)
    pod = t.body(p.puenta, color=t.FG, font_size=t.skaluj(26)) if p.puenta else None

    stan = {"przyjeci": []}

    def takt_kropki(scene):
        return [t.LaggedStart(*[t.GrowFromCenter(d) for d in kropki], lag_ratio=0.004)]

    def takt_prog(scene):
        return [t.Create(prog), t.FadeIn(opis)]

    def takt_przyjeci(scene):
        stan["przyjeci"] = [d for d in kropki if d.get_y() > prog.get_y()]
        return [
            d.animate.set_color(kolor_ok).set_fill(opacity=1.0) for d in stan["przyjeci"]
        ]

    def takt_podniesienie(scene):
        cel = y_progu(p.prog_do)
        stan["cel"] = cel
        return [prog.animate.set_y(cel), opis.animate.shift(t.UP * (cel - prog.get_y()))]

    def takt_odpadli(scene):
        cel = stan.get("cel", y_progu(p.prog_do))
        odpadli = [d for d in stan["przyjeci"] if d.get_y() < cel]
        anim = [d.animate.set_color(kolor_nie).set_fill(opacity=0.4) for d in odpadli]
        if pod is not None:
            anim.append(t.FadeIn(pod))
        return anim or None

    beaty = [
        Beat("kropki", 0.30, takt_kropki),
        Beat("prog", 0.14, takt_prog),
        Beat("przyjeci", 0.16, takt_przyjeci),
        Beat(
            "podniesienie",
            0.24,
            takt_podniesienie,
            rate_func=t.rate_functions.ease_in_out_cubic,
        ),
        Beat("odpadli", 0.16, takt_odpadli),
    ]

    return Kompozycja(
        rdzen=rdzen,
        pod=pod,
        beaty=beaty,
        kontrola={"siatka": kropki, "puenta": pod},
        moze_nachodzic=("prog", "opis_progu"),
    )


SIATKA_JEDNOSTEK = Szablon(
    nazwa="siatka_jednostek",
    opis="Kratki albo kropki z wypełnianiem etapami — „ile to jest” policzalnie.",
    Parametry=SiatkaParametry,
    zbuduj=_siatka_jednostek,
    pokrywa="punkty arkusza, top X% kandydatów",
    przyklad={
        "ilosc": 100,
        "kolumny": 10,
        "podpis": "100 kandydatów",
        "etapy": [{"od": 0, "ile": 5, "kolor": "akcent"}],
        "licznik": {"etykieta": "trzeba być w top", "od": 4.9, "do": 4.1,
                     "liczba_cyfr": 1, "sufiks": "%"},
    },
)

SIATKA_PROGU = Szablon(
    nazwa="siatka_progu",
    opis="Kropki kandydatów i ruchoma linia progu — kto wypada po podniesieniu.",
    Parametry=SiatkaProguParametry,
    zbuduj=_siatka_progu,
    pokrywa="mechanika progu rekrutacyjnego",
    przyklad={"kolumny": 9, "wiersze": 11, "puenta": "liczy się,\nilu ma lepiej"},
)

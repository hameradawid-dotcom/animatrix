"""Wspólne helpery wizualne projektu.

Importowany przez KAŻDĄ scenę (`from theme import *`). Kolory, fonty i rozmiary
przychodzą z `motyw.py` — to on decyduje, czy film wygląda jak
korepetytorhamera.pl, czy jak neutralny materiał na ciemnym tle.

Oba pliki należą do projektu — możesz je edytować. `animatrix` nie nadpisze ich
przy kolejnych uruchomieniach (chyba że wywołasz `animatrix sync-runtime --force`).
"""

from __future__ import annotations

import os

from manim import *  # noqa: F403

from motyw import *  # noqa: F403
from voice import speech_service  # noqa: F401  (re-eksport dla scen)

config.background_color = BG

_WAGI = {"NORMAL": NORMAL, "MEDIUM": MEDIUM, "SEMIBOLD": SEMIBOLD, "BOLD": BOLD}

# Kadr znamy dopiero po sparsowaniu flag Manima, więc czytamy go z configu,
# a nie z motywu. Rozmiary fontów są w jednostkach wysokości kadru — przy 9:16
# kadr jest wąski (4.5 jednostki zamiast 14.2), więc te same rozmiary wychodzą
# poza ekran. Stąd współczynnik.
# Manim NIE przelicza frame_width po zmianie rozdzielczości flagą -r: przy
# 1080x1920 kadr dalej zgłasza 14.22 x 8 i cała scena renderuje się ściśnięta.
# Dlatego wymuszamy kadr zgodny z proporcją pikseli.
config.frame_height = 8.0
config.frame_width = config.frame_height * config.pixel_width / config.pixel_height

KADR_W = config.frame_width
KADR_H = config.frame_height
PION = KADR_W < KADR_H

# Ile pikseli przypada na jednostkę Manima w DOCELOWEJ rozdzielczości formatu
# (1080p poziomo, 1920p pionowo). Liczone ze stałej referencyjnej, a nie
# z config.pixel_height, bo inaczej render roboczy -ql miałby inny layout niż
# finalny -qh.
PX_NA_JEDNOSTKE = (1920 if PION else 1080) / KADR_H

# Fonty zostają w rozmiarze bazowym również w pionie: kadr 9:16 ogląda się na
# telefonie, więc duży tekst jest zaletą. Wąski kadr wymusza natomiast KRÓTKIE
# linie — tekst łam ręcznie, nie zmniejszaj go.
SKALA_FONTU = 1.0


def skaluj(bazowy: int) -> int:
    return max(8, int(round(bazowy * SKALA_FONTU)))


# --------------------------------------------------------------------------
# Odstępy — wyłącznie ze skali marki
# --------------------------------------------------------------------------
def sp(px: int) -> float:
    """Zamienia odstęp z BRAND.md (w px) na jednostki Manima.

    Podanie wartości spoza skali jest błędem, a nie zaokrągleniem — inaczej
    layout rozjeżdża się względem strony.
    """
    if px not in SKALA_PX:
        raise ValueError(f"{px}px jest poza skalą odstępów {SKALA_PX}")
    return px / PX_NA_JEDNOSTKE


# --------------------------------------------------------------------------
# LaTeX z polskimi znakami
#
# Domyślny TexTemplate Manima nie ma T1+lmodern, więc "ł" i "ą" wychodzą puste
# albo wysypują kompilację. TEX_PL to naprawia. Używaj go WYŁĄCZNIE tam, gdzie
# naprawdę potrzebujesz LaTeXa (wzory); do zwykłego tekstu używaj `Text`.
# --------------------------------------------------------------------------
TEX_PL = TexTemplate(
    tex_compiler="latex",
    output_format=".dvi",
    preamble=r"""
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage{amsmath}
\usepackage{amssymb}
""",
)
config.tex_template = TEX_PL


# --------------------------------------------------------------------------
# Tekst
# --------------------------------------------------------------------------
def _tracking_markup(tekst: str, spacing: int) -> str:
    """Pango liczy letter_spacing w 1024-tych punkta i NIE skaluje go razem
    z `font_size` Manima — dlatego motyw podaje tę wartość wprost, a nie w em."""
    escaped = tekst.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<span letter_spacing="{spacing}">{escaped}</span>'


def tytul(tekst: str, **kw) -> MarkupText:
    kw.setdefault("font", FONT_HEAD)
    kw.setdefault("font_size", skaluj(ROZMIAR_TYTUL))
    kw.setdefault("weight", _WAGI[WAGA_TYTUL])
    kw.setdefault("color", FG)
    return MarkupText(_tracking_markup(tekst, TRACKING_TYTUL), **kw)


def podtytul(tekst: str, **kw) -> Text:
    kw.setdefault("font", FONT_UI)
    kw.setdefault("font_size", skaluj(ROZMIAR_PODTYTUL))
    kw.setdefault("weight", _WAGI[WAGA_PODTYTUL])
    kw.setdefault("color", FG_2)
    return Text(tekst, **kw)


def body(tekst: str, **kw) -> Text:
    kw.setdefault("font", FONT_UI)
    kw.setdefault("font_size", skaluj(ROZMIAR_BODY))
    kw.setdefault("weight", _WAGI[WAGA_BODY])
    kw.setdefault("color", FG)
    return Text(tekst, **kw)


def etykieta(tekst: str, **kw) -> Text:
    kw.setdefault("font", FONT_UI)
    kw.setdefault("font_size", skaluj(ROZMIAR_ETYKIETA))
    kw.setdefault("color", MUTED)
    return Text(tekst, **kw)


def tag(tekst: str, **kw) -> Text:
    """Krótki eyebrow tag — jedyne miejsce, gdzie marka dopuszcza wersaliki."""
    kw.setdefault("font", FONT_UI)
    kw.setdefault("font_size", skaluj(16))
    kw.setdefault("weight", SEMIBOLD)
    kw.setdefault("color", ACCENT)
    return Text(tekst.upper(), **kw)


def mono(tekst: str, **kw) -> Text:
    """Etykieta techniczna monospace — numery sekcji, oznaczenia, jednostki."""
    kw.setdefault("font", FONT_MONO)
    kw.setdefault("font_size", skaluj(ROZMIAR_ETYKIETA))
    kw.setdefault("color", MUTED)
    return Text(tekst, **kw)


def wzor(tex: str, **kw) -> MathTex:
    """Wzór matematyczny/chemiczny przez LaTeX. Bez polskich słów w środku."""
    kw.setdefault("color", FG)
    kw.setdefault("tex_template", TEX_PL)
    return MathTex(tex, **kw)


# --------------------------------------------------------------------------
# Liczby — zawsze animowane, nigdy statyczne
# --------------------------------------------------------------------------
def licznik(
    tracker: ValueTracker,
    *,
    liczba_cyfr: int = 0,
    kolor: str | None = None,
    rozmiar: int | None = None,
    sufiks: str = "",
    grupowanie: bool = False,
    docelowa: float | None = None,
) -> DecimalNumber:
    """DecimalNumber podpięty pod ValueTracker. Wystarczy `self.add(licznik(t))`
    i animować `t`.

    `grupowanie=True` wstawia PRZECINEK jako separator tysięcy — po polsku to
    czyta się jak część dziesiętną, więc domyślnie jest wyłączone. Duże liczby
    podawaj w tysiącach/milionach: `licznik(t, liczba_cyfr=1, sufiks=" mln")`.
    """
    num = DecimalNumber(
        docelowa if docelowa is not None else tracker.get_value(),
        num_decimal_places=liczba_cyfr,
        color=kolor or ACCENT,
        font_size=rozmiar or skaluj(ROZMIAR_LICZBA),
        group_with_commas=grupowanie,
        include_sign=False,
        unit=sufiks or None,
    )

    # DecimalNumber przebudowuje glify przy każdej zmianie wartości i potrafi
    # przy tym odpłynąć w bok. Kotwiczymy go na pozycji z pierwszej klatki —
    # czyli już po tym, jak scena ustawiła layout.
    kotwica: list = []

    def _aktualizuj(m: DecimalNumber) -> None:
        if not kotwica:
            kotwica.append(m.get_center().copy())
        m.set_value(tracker.get_value())
        m.move_to(kotwica[0])

    num.add_updater(_aktualizuj)
    return num


def animuj_liczbe(scene: Scene, tracker: ValueTracker, do: float, czas: float) -> None:
    scene.play(tracker.animate.set_value(do), run_time=czas, rate_func=rate_functions.ease_out_cubic)


# --------------------------------------------------------------------------
# Kompozycja
# --------------------------------------------------------------------------
def pasek_tytulu(tekst: str, podtytul_tekst: str = "") -> VGroup:
    t = tytul(tekst)
    grupa = VGroup(t)
    if podtytul_tekst:
        grupa = VGroup(t, podtytul(podtytul_tekst)).arrange(DOWN, buff=sp(16), aligned_edge=LEFT)
    grupa.to_edge(UP, buff=sp(64)).to_edge(LEFT, buff=sp(96))
    return grupa


def podkreslenie(mobject: Mobject, kolor: str | None = None) -> Line:
    return Line(
        mobject.get_corner(DOWN + LEFT),
        mobject.get_corner(DOWN + RIGHT),
        color=kolor or ACCENT,
        stroke_width=5,
    ).shift(DOWN * sp(16))


def karta(
    zawartosc: Mobject,
    *,
    kolor: str | None = None,
    obrys: str | None = None,
    padding: int = 32,
) -> VGroup:
    """Zaokrąglone tło pod treścią. Biel jest dozwolona TYLKO tutaj — nigdy jako
    tło sceny."""
    tlo = RoundedRectangle(
        corner_radius=sp(12),
        width=zawartosc.width + 2 * sp(padding),
        height=zawartosc.height + 2 * sp(padding),
        fill_color=kolor or POWIERZCHNIA,
        fill_opacity=1.0,
        stroke_color=obrys or SIATKA,
        stroke_width=1.5,
    ).move_to(zawartosc)
    return VGroup(tlo, zawartosc)


def linia(szerokosc: float = 4.0, kolor: str | None = None) -> Line:
    return Line(LEFT * szerokosc / 2, RIGHT * szerokosc / 2, color=kolor or SIATKA, stroke_width=1.5)


def pasek_misji(numer: int, etykieta: str) -> VGroup:
    """Znacznik sekcji w lewym górnym rogu.

    W motywie `misja` czyta się jak nagłówek briefingu, w pozostałych jak
    zwykły eyebrow tag. Sceny wołają to samo — różnicę robi motyw.
    """
    if STYL == "misja":
        oznaczenie = mono(f"// ZADANIE {numer:02d}", color=ACCENT)
        opis = mono(etykieta.upper(), color=FG_2)
        # W kadrze 9:16 nie ma miejsca na oznaczenie i opis w jednej linii.
        if PION:
            wiersz = VGroup(oznaczenie, opis).arrange(DOWN, buff=sp(8), aligned_edge=LEFT)
        else:
            wiersz = VGroup(oznaczenie, opis).arrange(RIGHT, buff=sp(16))
        maks = KADR_W - 2 * sp(64)
        if wiersz.width > maks:
            wiersz.scale(maks / wiersz.width)
        kreska = Line(
            wiersz.get_left() + DOWN * sp(12),
            wiersz.get_right() + DOWN * sp(12),
            color=SIATKA,
            stroke_width=1.5,
        )
        grupa = VGroup(wiersz, kreska)
    else:
        grupa = VGroup(tag(etykieta))
    return grupa.to_edge(UP, buff=sp(48)).to_edge(LEFT, buff=sp(64))


def naroza(mobject: Mobject, *, kolor: str | None = None, dlugosc: float = 0.35, margines: int = 24) -> VGroup:
    """Narożniki celownika wokół obiektu — kadrowanie jak w podglądzie operacyjnym."""
    kolor = kolor or ACCENT
    m = sp(margines)
    lewo, prawo = mobject.get_left()[0] - m, mobject.get_right()[0] + m
    dol, gora = mobject.get_bottom()[1] - m, mobject.get_top()[1] + m

    grupa = VGroup()
    for x, kier_x in ((lewo, 1), (prawo, -1)):
        for y, kier_y in ((dol, 1), (gora, -1)):
            rog = np.array([x, y, 0.0])
            grupa.add(
                Line(rog, rog + np.array([kier_x * dlugosc, 0.0, 0.0]), color=kolor, stroke_width=2.5),
                Line(rog, rog + np.array([0.0, kier_y * dlugosc, 0.0]), color=kolor, stroke_width=2.5),
            )
    return grupa


def wejscie(mobject: Mobject, **kw) -> Animation:
    """Wejście obiektu w stylistyce motywu.

    `misja` odsłania treść (Write / narastanie), pozostałe motywy wprowadzają
    ją miękkim FadeIn z lekkim przesunięciem.
    """
    if STYL == "misja":
        # Create obrysowuje litery zamiast je pisać, więc wszystko, co zawiera
        # tekst — nawet głęboko w grupie — idzie przez Write.
        return Write(mobject, **kw) if _zawiera_tekst(mobject) else Create(mobject, **kw)
    kw.setdefault("shift", UP * sp(16))
    return FadeIn(mobject, **kw)


def _zawiera_tekst(mobject: Mobject) -> bool:
    if isinstance(mobject, (Text, MarkupText, MathTex, Tex)):
        return True
    return any(_zawiera_tekst(sub) for sub in mobject.submobjects)


def osie(x_range: list[float], y_range: list[float], **kw) -> Axes:
    kw.setdefault("axis_config", {"color": SIATKA, "stroke_width": 2, "include_tip": False})
    kw.setdefault("x_length", 8)
    kw.setdefault("y_length", 4.5)
    return Axes(x_range=x_range, y_range=y_range, **kw)


def svg(sciezka: str, **kw) -> SVGMobject:
    """Mapa / ikona z pliku SVG (np. wygenerowana przez `animatrix assets map-pl`)."""
    kw.setdefault("stroke_color", SIATKA)
    kw.setdefault("stroke_width", 1.2)
    kw.setdefault("fill_color", BG_ALT)
    kw.setdefault("fill_opacity", 1.0)
    return SVGMobject(sciezka, **kw)


def svg_regiony(sciezka_svg: str) -> tuple[SVGMobject, dict[str, VMobject]]:
    """Wczytuje mapę i mapuje nazwy regionów na podobiekty.

    Manim nie zachowuje atrybutów `id` z SVG, więc nazwy biorą się z sidecar-owego
    JSON-a o tej samej nazwie (`assets/poland.json`), gdzie kolejność wpisów
    odpowiada kolejności ścieżek w SVG. Oba pliki generuje `animatrix assets map-pl`.
    """
    import json
    from pathlib import Path as _Path

    mapa = svg(sciezka_svg)
    meta = _Path(sciezka_svg).with_suffix(".json")
    nazwy: list[str] = []
    if meta.exists():
        nazwy = json.loads(meta.read_text(encoding="utf-8")).get("regiony", [])
    regiony = {n: sub for n, sub in zip(nazwy, mapa.submobjects)}
    return mapa, regiony


def skala_koloru(wartosc: float, minimum: float, maksimum: float, *, od=None, do=None) -> ManimColor:
    span = (maksimum - minimum) or 1.0
    return interpolate_color(
        ManimColor(od or BG_ALT), ManimColor(do or ACCENT), (wartosc - minimum) / span
    )


def pokoloruj_regiony(
    regiony: dict[str, VMobject],
    wartosci: dict[str, float],
    *,
    od=None,
    do=None,
    brak=None,
) -> None:
    """Koloruje regiony danymi w skali liniowej min..max. Regiony bez danych dostają `brak`."""
    for sub in regiony.values():
        sub.set_fill(ManimColor(brak or BG_ALT), opacity=1.0)
    if not wartosci:
        return
    lo, hi = min(wartosci.values()), max(wartosci.values())
    for nazwa, wartosc in wartosci.items():
        sub = regiony.get(nazwa)
        if sub is not None:
            sub.set_fill(skala_koloru(wartosc, lo, hi, od=od, do=do), opacity=1.0)


# --------------------------------------------------------------------------
# Kontrola układu
#
# Most między Manimem a `animatrix.uklad`. Scena podaje nazwane obiekty, my
# wyciągamy z nich prostokąty i sprawdzamy kadr, strefę bezpieczną, kolizje
# i czytelność tekstu. Uchybienia lecą na stderr, więc widać je w logu renderu
# i w interfejsie — a przy ANIMATRIX_STRICT=1 render się na nich zatrzymuje.
# --------------------------------------------------------------------------
def prostokat_z(mobject: Mobject):
    from animatrix.uklad import Prostokat

    lewo, dol = mobject.get_corner(DOWN + LEFT)[:2]
    prawo, gora = mobject.get_corner(UP + RIGHT)[:2]
    return Prostokat(float(lewo), float(dol), float(prawo), float(gora))


def kadr_sceny():
    from animatrix.uklad import Kadr

    from animatrix.formaty import format_wideo

    nazwa = os.environ.get("ANIMATRIX_FORMAT") or ("9:16" if PION else "16:9")
    try:
        fmt = format_wideo(nazwa)
    except Exception:
        fmt = format_wideo("9:16" if PION else "16:9")
    return Kadr(
        szerokosc=KADR_W,
        wysokosc=KADR_H,
        px_na_jednostke=PX_NA_JEDNOSTKE,
        strefa=fmt.strefa_bezpieczna(),
    )


def sprawdz_uklad(elementy: dict, *, moze_nachodzic: tuple = ()) -> list:
    """Waliduje kompozycję PRZED renderem. `elementy` to {nazwa: mobject}."""
    import sys as _sys

    from animatrix.uklad import Element, podsumowanie, waliduj

    kadr = kadr_sceny()
    lista = [
        Element(
            id=nazwa,
            prostokat=prostokat_z(m),
            tekst=_zawiera_tekst(m),
            rozmiar_px=float(m.height) * PX_NA_JEDNOSTKE if _zawiera_tekst(m) else None,
            moze_nachodzic=nazwa in moze_nachodzic,
        )
        for nazwa, m in elementy.items()
        if m is not None
    ]
    uchybienia = waliduj(lista, kadr)
    if uchybienia:
        print(f"[uklad] {podsumowanie(uchybienia)}", file=_sys.stderr)
        for u in uchybienia:
            print(f"[uklad] {u}", file=_sys.stderr)
        if os.environ.get("ANIMATRIX_STRICT") == "1":
            twarde = [u for u in uchybienia if u.waga == "blad"]
            if twarde:
                raise RuntimeError(
                    "Układ sceny ma błędy: " + "; ".join(u.opis for u in twarde)
                )
    return uchybienia

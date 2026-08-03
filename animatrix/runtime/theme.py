"""Wspólny motyw wizualny projektu.

Importowany przez KAŻDĄ scenę (`from theme import *`). Zmiana koloru albo fontu
tutaj propaguje się na wszystkie sceny bez dotykania ich kodu.

Ten plik należy do projektu — możesz go edytować. `animatrix` nie nadpisze go
przy kolejnych uruchomieniach (chyba że wywołasz `animatrix sync-runtime --force`).
"""

from __future__ import annotations

from manim import *  # noqa: F403

from voice import speech_service  # noqa: F401  (re-eksport dla scen)

# --------------------------------------------------------------------------
# Paleta — ciemne tło, czysta wektorowa estetyka
# --------------------------------------------------------------------------
BG = "#0E1116"
FG = "#E9EDF2"
MUTED = "#8B96A8"
GRID = "#1E2632"

ACCENT = "#4CC9F0"       # główny akcent
ACCENT_2 = "#F72585"     # kontrast / uwaga
ACCENT_3 = "#FFD166"     # wyróżnienie liczby
OK = "#06D6A0"
WARN = "#EF476F"

PALETA = [ACCENT, ACCENT_3, OK, ACCENT_2, WARN]

# --------------------------------------------------------------------------
# Typografia
#
# Polskie diakrytyki: `Text` renderuje przez Pango i obsługuje ą/ć/ę/ł/ń/ó/ś/ź/ż
# bez żadnej konfiguracji, o ile font je zawiera. DejaVu Sans zawiera.
# NIE używaj `Tex`/`Text` z LaTeXem do polskiej prozy — patrz TEX_PL niżej.
# --------------------------------------------------------------------------
FONT_UI = "DejaVu Sans"
FONT_MONO = "DejaVu Sans Mono"

ROZMIAR_TYTUL = 44
ROZMIAR_PODTYTUL = 30
ROZMIAR_BODY = 26
ROZMIAR_LICZBA = 84

config.background_color = BG

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


def _apply_tex_default() -> None:
    config.tex_template = TEX_PL


_apply_tex_default()


# --------------------------------------------------------------------------
# Tekst
# --------------------------------------------------------------------------
def tytul(tekst: str, **kw) -> Text:
    kw.setdefault("font", FONT_UI)
    kw.setdefault("font_size", ROZMIAR_TYTUL)
    kw.setdefault("weight", BOLD)
    kw.setdefault("color", FG)
    return Text(tekst, **kw)


def podtytul(tekst: str, **kw) -> Text:
    kw.setdefault("font", FONT_UI)
    kw.setdefault("font_size", ROZMIAR_PODTYTUL)
    kw.setdefault("color", MUTED)
    return Text(tekst, **kw)


def body(tekst: str, **kw) -> Text:
    kw.setdefault("font", FONT_UI)
    kw.setdefault("font_size", ROZMIAR_BODY)
    kw.setdefault("color", FG)
    return Text(tekst, **kw)


def etykieta(tekst: str, **kw) -> Text:
    kw.setdefault("font", FONT_UI)
    kw.setdefault("font_size", 20)
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
    kolor: str = ACCENT_3,
    rozmiar: int = ROZMIAR_LICZBA,
    sufiks: str = "",
    grupowanie: bool = False,
) -> DecimalNumber:
    """DecimalNumber podpięty pod ValueTracker. Wystarczy `self.add(licznik(t))`
    i animować `t`.

    `grupowanie=True` wstawia PRZECINEK jako separator tysięcy — po polsku to
    czyta się jak część dziesiętną, więc domyślnie jest wyłączone. Duże liczby
    podawaj w tysiącach/milionach: `licznik(t, liczba_cyfr=1, sufiks=" mln")`.
    """
    num = DecimalNumber(
        tracker.get_value(),
        num_decimal_places=liczba_cyfr,
        color=kolor,
        font_size=rozmiar,
        group_with_commas=grupowanie,
        include_sign=False,
        unit=sufiks or None,
    )
    num.add_updater(lambda m: m.set_value(tracker.get_value()))
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
        p = podtytul(podtytul_tekst)
        grupa = VGroup(t, p).arrange(DOWN, buff=0.22, aligned_edge=LEFT)
    grupa.to_edge(UP, buff=0.6).to_edge(LEFT, buff=0.9)
    return grupa


def podkreslenie(mobject: Mobject, kolor: str = ACCENT) -> Line:
    return Line(
        mobject.get_corner(DOWN + LEFT),
        mobject.get_corner(DOWN + RIGHT),
        color=kolor,
        stroke_width=5,
    ).shift(DOWN * 0.15)


def karta(zawartosc: Mobject, kolor: str = GRID, padding: float = 0.35) -> VGroup:
    tlo = RoundedRectangle(
        corner_radius=0.15,
        width=zawartosc.width + 2 * padding,
        height=zawartosc.height + 2 * padding,
        fill_color=kolor,
        fill_opacity=1.0,
        stroke_width=0,
    ).move_to(zawartosc)
    return VGroup(tlo, zawartosc)


def osie(
    x_range: list[float],
    y_range: list[float],
    **kw,
) -> Axes:
    kw.setdefault("axis_config", {"color": MUTED, "stroke_width": 2, "include_tip": False})
    kw.setdefault("x_length", 8)
    kw.setdefault("y_length", 4.5)
    return Axes(x_range=x_range, y_range=y_range, **kw)


def svg(sciezka: str, **kw) -> SVGMobject:
    """Mapa / ikona z pliku SVG (np. wygenerowana przez `animatrix assets map-pl`)."""
    kw.setdefault("stroke_color", MUTED)
    kw.setdefault("stroke_width", 1.2)
    kw.setdefault("fill_color", GRID)
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


def pokoloruj_regiony(
    regiony: dict[str, VMobject],
    wartosci: dict[str, float],
    *,
    od=GRID,
    do=ACCENT,
    brak=GRID,
) -> None:
    """Koloruje regiony danymi w skali liniowej min..max. Regiony bez danych dostają `brak`."""
    for sub in regiony.values():
        sub.set_fill(ManimColor(brak), opacity=1.0)
    if not wartosci:
        return
    lo, hi = min(wartosci.values()), max(wartosci.values())
    span = (hi - lo) or 1.0
    for nazwa, wartosc in wartosci.items():
        sub = regiony.get(nazwa)
        if sub is None:
            continue
        t = (wartosc - lo) / span
        sub.set_fill(interpolate_color(ManimColor(od), ManimColor(do), t), opacity=1.0)

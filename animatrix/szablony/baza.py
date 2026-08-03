"""Wspólny szkielet szablonów: sloty, tempo i składanie kadru.

Sedno problemu, który to naprawia: każda dotychczasowa scena ustawiała się
ręcznie (`.move_to(UP * 1.1)`, `next_to(..., buff=sp(96))`, `SKALA = 0.011`),
więc kompozycja zależała od tego, jak model akurat trafił z liczbami — i przy
zmianie formatu rozjeżdżała się w całości.

Tutaj szablon buduje wyłącznie SWOJĄ zawartość i wkłada ją do slotów. Pozycję,
odstępy i przeskalowanie do strefy bezpiecznej ustala jeden składacz, ten sam
dla wszystkich szablonów i wszystkich formatów.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from animatrix.scena import KOLORY, SceneSpec

# Odstępy między slotami — wyłącznie ze skali marki.
BUFF_NAD = 32
BUFF_POD = 48
BUFF_STOPKA = 24
BUFF_POD_NAGLOWKIEM = 48

# Kompozycja z zapasem w kadrze jest dociągana do strefy bezpiecznej — na
# telefonie drobna treść na środku ekranu po prostu przelatuje niezauważona.
# Limit jest po to, żeby scena z jednym słowem nie urosła do plakatu.
MAKS_POWIEKSZENIE = 1.3


class SzablonError(RuntimeError):
    pass


@dataclass
class Kontekst:
    """Wszystko, czego szablon potrzebuje poza własnymi parametrami."""

    t: Any  # moduł `theme` projektu (import dopiero w podprocesie renderu)
    kadr: Any  # animatrix.uklad.Kadr
    spec: SceneSpec
    dane: Any = None  # moduł `dane.py` projektu, jeśli istnieje

    def kolor(self, nazwa: str | None, domyslny: str = "akcent") -> Any:
        nazwa = nazwa or domyslny
        if isinstance(nazwa, str) and nazwa.startswith("#"):
            return nazwa
        atrybut = KOLORY.get(nazwa)
        if atrybut is None:
            raise SzablonError(
                f"Nie znam koloru '{nazwa}'. Dostępne: {', '.join(sorted(KOLORY))}"
            )
        return getattr(self.t, atrybut)

    def wartosc(self, x: Any) -> Any:
        """Liczba wprost albo odwołanie do `dane.py` w postaci "@NAZWA".

        Odwołania trzymają film przy udokumentowanych źródłach (ZRODLA.md),
        a jednocześnie interfejs pokazuje rozwiniętą wartość.
        """
        if isinstance(x, str) and x.startswith("@"):
            nazwa = x[1:]
            if self.dane is None:
                raise SzablonError(f"Odwołanie {x} wymaga pliku dane.py w projekcie.")
            if not hasattr(self.dane, nazwa):
                raise SzablonError(f"dane.py nie ma wartości '{nazwa}'.")
            return getattr(self.dane, nazwa)
        if isinstance(x, list):
            return [self.wartosc(e) for e in x]
        return x


@dataclass
class Beat:
    """Jeden takt sceny. `udzial` to ułamek `tracker.duration`."""

    nazwa: str
    udzial: float
    fabryka: Callable[[Any], Sequence[Any] | None]
    rate_func: Any = None
    lag_ratio: float | None = None


@dataclass
class Kompozycja:
    """Wynik pracy szablonu: co jest w kadrze i co się dzieje."""

    rdzen: Any
    beaty: list[Beat]
    nad: Any = None
    pod: Any = None
    stopka: Any = None
    # Elementy wewnątrz rdzenia, które walidator ma sprawdzać osobno.
    kontrola: dict[str, Any] = field(default_factory=dict)
    moze_nachodzic: tuple[str, ...] = ()
    # Szablon może zażądać, żeby nie skalować rdzenia (siatki, mapy).
    skaluj_rdzen: bool = True


@dataclass
class Szablon:
    nazwa: str
    opis: str
    Parametry: type
    zbuduj: Callable[[Kontekst, Any], Kompozycja]
    pokrywa: str = ""
    # Komplet parametrów, który ma się zbudować w każdym formacie i motywie.
    # Służy za punkt startowy w interfejsie i za dane do testu tabelarycznego.
    przyklad: dict[str, Any] = field(default_factory=dict)

    def schemat(self) -> dict[str, Any]:
        """JSON Schema parametrów — z tego interfejs generuje formularz."""
        return self.Parametry.model_json_schema()


def naglowek_sekcji(k: Kontekst):
    if k.spec.sekcja is None:
        return None
    return k.t.pasek_misji(k.spec.sekcja.numer, k.spec.sekcja.etykieta)


def zloz(k: Kontekst, komp: Kompozycja, naglowek=None) -> dict[str, Any]:
    """Ustawia sloty w strefie bezpiecznej. Zwraca mapę {nazwa: mobject}.

    Nagłówek trafia do lewego górnego rogu STREFY BEZPIECZNEJ, nie kadru —
    właśnie dlatego dotychczasowe sceny miały pasek pod interfejsem TikToka.
    """
    t = k.t
    bezpieczny = k.kadr.bezpieczny()

    gorny_limit = bezpieczny.y1
    if naglowek is not None:
        naglowek.move_to(
            [
                bezpieczny.x0 + naglowek.width / 2,
                bezpieczny.y1 - naglowek.height / 2,
                0.0,
            ]
        )
        gorny_limit = naglowek.get_bottom()[1] - t.sp(BUFF_POD_NAGLOWKIEM)

    stos = t.VGroup()
    poprzedni = None
    for element, buff in (
        (komp.nad, None),
        (komp.rdzen, BUFF_NAD),
        (komp.pod, BUFF_POD),
        (komp.stopka, BUFF_STOPKA),
    ):
        if element is None:
            continue
        if poprzedni is not None:
            element.next_to(poprzedni, t.DOWN, buff=t.sp(buff))
        stos.add(element)
        poprzedni = element

    if not stos.submobjects:
        raise SzablonError("Szablon nie zwrócił żadnej treści.")

    wolna_wysokosc = gorny_limit - bezpieczny.y0
    if wolna_wysokosc <= 0:
        raise SzablonError("Nagłówek zajął całą strefę bezpieczną.")

    wspolczynnik = min(
        MAKS_POWIEKSZENIE,
        wolna_wysokosc / stos.height if stos.height > 0 else 1.0,
        bezpieczny.szerokosc / stos.width if stos.width > 0 else 1.0,
    )
    if abs(wspolczynnik - 1.0) > 0.01:
        stos.scale(wspolczynnik)

    stos.move_to(
        [
            (bezpieczny.x0 + bezpieczny.x1) / 2,
            (bezpieczny.y0 + gorny_limit) / 2,
            0.0,
        ]
    )

    elementy: dict[str, Any] = {}
    if naglowek is not None:
        elementy["naglowek"] = naglowek
    for nazwa, element in (("nad", komp.nad), ("pod", komp.pod), ("stopka", komp.stopka)):
        if element is not None:
            elementy[nazwa] = element
    if komp.kontrola:
        elementy.update(komp.kontrola)
    else:
        elementy["rdzen"] = komp.rdzen
    return elementy


def tempo(komp: Kompozycja, spec: SceneSpec) -> list[Beat]:
    """Nakłada nadpisania tempa ze specu na domyślne udziały szablonu."""
    if not spec.tempo:
        return komp.beaty
    nieznane = set(spec.tempo) - {b.nazwa for b in komp.beaty}
    if nieznane:
        raise SzablonError(
            f"Szablon '{spec.szablon}' nie ma taktów: {', '.join(sorted(nieznane))}. "
            f"Dostępne: {', '.join(b.nazwa for b in komp.beaty)}"
        )
    return [
        Beat(b.nazwa, spec.tempo.get(b.nazwa, b.udzial), b.fabryka, b.rate_func, b.lag_ratio)
        for b in komp.beaty
    ]

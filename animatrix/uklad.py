"""Silnik układu: regiony kadru i walidacja kompozycji przed renderem.

Ten moduł CELOWO nie importuje Manima. Operuje na prostokątach, więc da się go
testować bez renderowania czegokolwiek — a walidacja kosztuje milisekundy
zamiast dwóch minut renderu, po których i tak widać, że napisy na siebie wchodzą.

Most do Manima jest w `runtime/theme.py` (funkcja `zbierz_elementy`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Literal

from animatrix.formaty import Format, StrefaBezpieczna, format_wideo

Waga = Literal["blad", "ostrzezenie"]

# Poniżej tego progu tekst na telefonie jest nieczytelny. Wartość w pikselach
# DOCELOWEGO renderu, nie roboczego.
MIN_TEKST_PX = 28

# Ile procent mniejszego z dwóch prostokątów musi się pokryć, żeby uznać to za
# kolizję. Bbox to prostokąt opisany na obiekcie, więc mapa albo łamana mają
# w nim sporo pustego miejsca — bez progu sypałoby fałszywymi alarmami.
PROG_KOLIZJI = 0.12

# Element o polu mniejszym niż ten ułamek sąsiada to marker (kropka na łamanej,
# grot strzałki, przecinek osi) — leży na nim celowo i nie jest kolizją.
PROG_MARKERA = 0.05

# Luz przy sprawdzaniu zawierania — obrys ramki bywa o włos węższy od treści.
TOLERANCJA_ZAWIERANIA = 0.05


@dataclass(frozen=True)
class Prostokat:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def szerokosc(self) -> float:
        return self.x1 - self.x0

    @property
    def wysokosc(self) -> float:
        return self.y1 - self.y0

    @property
    def pole(self) -> float:
        return max(0.0, self.szerokosc) * max(0.0, self.wysokosc)

    def zawiera(self, inny: "Prostokat", tolerancja: float = 1e-6) -> bool:
        return (
            inny.x0 >= self.x0 - tolerancja
            and inny.x1 <= self.x1 + tolerancja
            and inny.y0 >= self.y0 - tolerancja
            and inny.y1 <= self.y1 + tolerancja
        )

    def czesc_wspolna(self, inny: "Prostokat") -> "Prostokat":
        return Prostokat(
            max(self.x0, inny.x0),
            max(self.y0, inny.y0),
            min(self.x1, inny.x1),
            min(self.y1, inny.y1),
        )

    def pokrycie(self, inny: "Prostokat") -> float:
        """Jaka część MNIEJSZEGO prostokąta leży we wspólnej powierzchni."""
        mniejszy = min(self.pole, inny.pole)
        if mniejszy <= 0:
            return 0.0
        return self.czesc_wspolna(inny).pole / mniejszy


@dataclass
class Element:
    """Pojedynczy obiekt kompozycji widziany przez walidator."""

    id: str
    prostokat: Prostokat
    tekst: bool = False
    rozmiar_px: float | None = None
    moze_nachodzic: bool = False


@dataclass(frozen=True)
class Uchybienie:
    waga: Waga
    kod: str
    element: str
    opis: str

    def __str__(self) -> str:
        znak = "BŁĄD" if self.waga == "blad" else "uwaga"
        return f"[{znak}] {self.element}: {self.opis}"


@dataclass(frozen=True)
class Kadr:
    """Kadr w jednostkach Manima plus wiedza o strefie bezpiecznej."""

    szerokosc: float
    wysokosc: float
    px_na_jednostke: float
    strefa: StrefaBezpieczna = field(default_factory=StrefaBezpieczna)

    @classmethod
    def z_formatu(cls, nazwa: str | None, wysokosc_jednostek: float = 8.0) -> "Kadr":
        fmt: Format = format_wideo(nazwa)
        return cls(
            szerokosc=wysokosc_jednostek * fmt.proporcja,
            wysokosc=wysokosc_jednostek,
            px_na_jednostke=fmt.wysokosc / wysokosc_jednostek,
            strefa=fmt.strefa_bezpieczna(),
        )

    def px(self, jednostki: float) -> float:
        return jednostki * self.px_na_jednostke

    def jednostki(self, px: float) -> float:
        return px / self.px_na_jednostke

    def pelny(self) -> Prostokat:
        return Prostokat(-self.szerokosc / 2, -self.wysokosc / 2, self.szerokosc / 2, self.wysokosc / 2)

    def bezpieczny(self) -> Prostokat:
        p = self.pelny()
        return Prostokat(
            p.x0 + self.jednostki(self.strefa.lewo),
            p.y0 + self.jednostki(self.strefa.dol),
            p.x1 - self.jednostki(self.strefa.prawo),
            p.y1 - self.jednostki(self.strefa.gora),
        )

    def region(self, nazwa: str) -> Prostokat:
        """Poziomy pas strefy bezpiecznej: gora / srodek / dol / pelny."""
        b = self.bezpieczny()
        if nazwa == "pelny":
            return b
        krok = b.wysokosc / 3
        pasy = {
            "gora": Prostokat(b.x0, b.y1 - krok, b.x1, b.y1),
            "srodek": Prostokat(b.x0, b.y0 + krok, b.x1, b.y1 - krok),
            "dol": Prostokat(b.x0, b.y0, b.x1, b.y0 + krok),
        }
        if nazwa not in pasy:
            raise ValueError(f"Nie znam regionu '{nazwa}'. Dostępne: gora, srodek, dol, pelny")
        return pasy[nazwa]


def waliduj(
    elementy: Iterable[Element],
    kadr: Kadr,
    *,
    min_tekst_px: float = MIN_TEKST_PX,
    prog_kolizji: float = PROG_KOLIZJI,
) -> list[Uchybienie]:
    """Sprawdza kompozycję przed renderem. Zwraca listę uchybień, nie rzuca."""
    elementy = list(elementy)
    uchybienia: list[Uchybienie] = []
    pelny = kadr.pelny()
    bezpieczny = kadr.bezpieczny()

    for el in elementy:
        if not pelny.zawiera(el.prostokat):
            uchybienia.append(
                Uchybienie("blad", "poza_kadrem", el.id, "wychodzi poza kadr — będzie ucięty")
            )
        elif not bezpieczny.zawiera(el.prostokat):
            uchybienia.append(
                Uchybienie(
                    "ostrzezenie",
                    "poza_strefa",
                    el.id,
                    "wchodzi w obszar zasłaniany przez interfejs platformy",
                )
            )

        if el.tekst and el.rozmiar_px is not None and el.rozmiar_px < min_tekst_px:
            uchybienia.append(
                Uchybienie(
                    "ostrzezenie",
                    "maly_tekst",
                    el.id,
                    f"tekst ma {el.rozmiar_px:.0f} px, próg czytelności na telefonie to {min_tekst_px:.0f} px",
                )
            )

    for i, a in enumerate(elementy):
        for b in elementy[i + 1 :]:
            if a.moze_nachodzic or b.moze_nachodzic:
                continue
            pola = sorted((a.prostokat.pole, b.prostokat.pole))
            if pola[1] > 0 and pola[0] / pola[1] < PROG_MARKERA:
                continue
            # Zawieranie to nie kolizja, tylko relacja: ramka wokół treści,
            # tło pod tekstem, podkreślenie pod nagłówkiem, kropki na łamanej.
            if a.prostokat.zawiera(b.prostokat, TOLERANCJA_ZAWIERANIA) or b.prostokat.zawiera(
                a.prostokat, TOLERANCJA_ZAWIERANIA
            ):
                continue
            pokrycie = a.prostokat.pokrycie(b.prostokat)
            if pokrycie > prog_kolizji:
                uchybienia.append(
                    Uchybienie(
                        "blad",
                        "kolizja",
                        f"{a.id} + {b.id}",
                        f"elementy nachodzą na siebie w {pokrycie * 100:.0f}%",
                    )
                )

    return uchybienia


def bledy(uchybienia: Iterable[Uchybienie]) -> list[Uchybienie]:
    return [u for u in uchybienia if u.waga == "blad"]


def podsumowanie(uchybienia: Iterable[Uchybienie]) -> str:
    uchybienia = list(uchybienia)
    if not uchybienia:
        return "układ bez zastrzeżeń"
    liczba_bledow = len(bledy(uchybienia))
    liczba_uwag = len(uchybienia) - liczba_bledow
    czesci = []
    if liczba_bledow:
        czesci.append(f"{liczba_bledow} błąd(y) układu")
    if liczba_uwag:
        czesci.append(f"{liczba_uwag} ostrzeżenie(a)")
    return ", ".join(czesci)

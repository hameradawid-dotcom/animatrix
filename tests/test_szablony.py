"""Testy modelu deklaratywnej sceny i katalogu szablonów.

Nie renderują niczego — sprawdzają kontrakt, na którym opiera się interfejs:
schemat parametrów, walidację specu i nazwy kolorów.
"""

import pytest
from pydantic import ValidationError

from animatrix import scena as scena_mod
from animatrix.scena import KOLORY, SceneSpec
from animatrix.szablony import KATALOG, SzablonError, szablon
from animatrix.szablony.baza import Beat, Kompozycja, tempo


def test_katalog_nie_jest_pusty():
    assert KATALOG
    assert all(s.nazwa == nazwa for nazwa, s in KATALOG.items())


def test_kazdy_szablon_ma_dzialajacy_przyklad():
    """Przykład to punkt startowy w interfejsie — musi przechodzić walidację."""
    for nazwa, s in KATALOG.items():
        assert s.przyklad, f"{nazwa} nie ma przykładowych parametrów"
        s.Parametry.model_validate(s.przyklad)


def test_kazdy_szablon_daje_schemat_dla_formularza():
    for nazwa, s in KATALOG.items():
        schemat = s.schemat()
        assert schemat.get("properties"), f"{nazwa} nie zwrócił pól do formularza"


def test_kolory_sa_nazwami_roli_nie_hexami():
    """Przełączenie motywu nie może wymagać dotykania scen."""
    for s in KATALOG.values():
        surowy = repr(s.przyklad)
        assert "#" not in surowy, f"{s.nazwa} ma hex w przykładzie zamiast nazwy koloru"
    for nazwa in ("akcent", "alarm", "wyroznienie", "stonowany"):
        assert nazwa in KOLORY


def test_nieznany_szablon_podpowiada_dostepne():
    with pytest.raises(SzablonError, match="Nie znam szablonu"):
        szablon("nie_ma_takiego")


# --- spec sceny ------------------------------------------------------------


def test_tempo_musi_sumowac_sie_do_jedynki():
    with pytest.raises(ValidationError, match="sumują się"):
        SceneSpec(id="s01", szablon="licznik_hero", parametry={"wartosc": 1}, tempo={"a": 0.5})


def test_tempo_puste_jest_ok():
    spec = SceneSpec(id="s01", szablon="licznik_hero", parametry={"wartosc": 1})
    assert spec.tempo == {}


def test_szablon_kod_wymaga_pliku_i_klasy():
    with pytest.raises(ValidationError, match="wymaga parametrów"):
        SceneSpec(id="s01", szablon="kod", parametry={"plik": "scenes/s01.py"})
    spec = SceneSpec(
        id="s01", szablon="kod", parametry={"plik": "scenes/s01.py", "klasa": "Scena_S01"}
    )
    assert spec.wlasny_kod


def test_hash_zmienia_sie_z_parametrami():
    a = SceneSpec(id="s01", szablon="licznik_hero", parametry={"wartosc": 1})
    b = SceneSpec(id="s01", szablon="licznik_hero", parametry={"wartosc": 2})
    assert a.hash() != b.hash()
    assert a.hash() == a.model_copy(deep=True).hash()


def test_zapis_i_odczyt_specu(tmp_path):
    spec = SceneSpec(
        id="s01",
        narracja="Dwieście pięćdziesiąt pięć miejsc.",
        szablon="licznik_hero",
        parametry={"wartosc": 255, "podpis": "/ 200 pkt"},
        sekcja={"numer": 1, "etykieta": "Skala"},
    )
    sciezka = scena_mod.sciezka_specu(tmp_path, "s01")
    scena_mod.zapisz(spec, sciezka)
    assert scena_mod.wczytaj(sciezka) == spec


# --- tempo -----------------------------------------------------------------


def _kompozycja():
    return Kompozycja(
        rdzen=object(),
        beaty=[Beat("wejscie", 0.3, lambda s: None), Beat("glowna", 0.7, lambda s: None)],
    )


def test_nadpisanie_tempa_zmienia_udzialy():
    spec = SceneSpec(
        id="s01",
        szablon="licznik_hero",
        parametry={"wartosc": 1},
        tempo={"wejscie": 0.6, "glowna": 0.4},
    )
    beaty = tempo(_kompozycja(), spec)
    assert [b.udzial for b in beaty] == [0.6, 0.4]


def test_nadpisanie_nieznanego_taktu_wyjasnia_ktore_istnieja():
    spec = SceneSpec(
        id="s01",
        szablon="licznik_hero",
        parametry={"wartosc": 1},
        tempo={"nieistniejacy": 1.0},
    )
    with pytest.raises(SzablonError, match="glowna"):
        tempo(_kompozycja(), spec)

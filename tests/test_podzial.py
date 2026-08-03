"""Testy podziału wklejonego scenariusza.

Scenariusze przychodzą z Claude/GPT jako blok tekstu — jedyne, co ten moduł ma
zrobić, to pociąć go na segmenty tak, żeby nie rozerwać liczby ani skrótu.
"""

import pytest

from animatrix.podzial import Kawalek, dlugosc_s, podziel, rozdziel, scal, zdania


def test_skrot_z_liczba_nie_konczy_zdania():
    assert zdania("Cel to ok. 170 pkt. Da się to policzyć.") == [
        "Cel to ok. 170 pkt.",
        "Da się to policzyć.",
    ]


def test_jednostka_konczy_zdanie_gdy_dalej_wielka_litera():
    """„256 tys. osób" to środek zdania, „321 tys. W 2027" to już nowe zdanie."""
    assert zdania("W 2025 zdawało 256 tys. osób. W 2026 już 321 tys. W 2027 będzie więcej.") == [
        "W 2025 zdawało 256 tys. osób.",
        "W 2026 już 321 tys.",
        "W 2027 będzie więcej.",
    ]


def test_inicjal_nie_konczy_zdania():
    assert zdania("Prowadzi D. Hamera. Zapraszamy.") == [
        "Prowadzi D. Hamera.",
        "Zapraszamy.",
    ]


def test_liczba_na_koncu_konczy_zdanie_przed_wielka_litera():
    assert zdania("Próg wyniósł 149. Rok później 159.") == [
        "Próg wyniósł 149.",
        "Rok później 159.",
    ]


def test_pusty_tekst_daje_pusta_liste():
    assert zdania("   \n  ") == []
    assert podziel("") == []


# --- segmentacja -----------------------------------------------------------


def test_puste_linie_sa_swiadoma_granica_segmentow():
    kawalki = podziel("Pierwsza myśl.\n\nDruga myśl.")
    assert [k.narracja for k in kawalki] == ["Pierwsza myśl.", "Druga myśl."]
    assert [k.id for k in kawalki] == ["s01", "s02"]


def test_krotkie_zdania_lacza_sie_w_jeden_segment():
    kawalki = podziel("Dwieście miejsc. Pięć tysięcy chętnych.")
    assert len(kawalki) == 1


def test_zaden_segment_nie_przekracza_limitu_gdy_da_sie_ciac():
    dlugie = (
        "Realny cel na Szczecin w 2027 to około stu siedemdziesięciu punktów, "
        "czyli osiemdziesiąt pięć procent z dwóch rozszerzeń, co przy obecnej "
        "dynamice progów jest wynikiem na granicy pewności."
    )
    for k in podziel(dlugie):
        assert k.znakow <= 165, k.narracja


def test_dlugosc_liczona_z_tempa_mowy():
    kawalki = podziel("Dwieście pięćdziesiąt pięć miejsc.")
    assert 1.0 < dlugosc_s(kawalki) < 5.0


def test_identyfikatory_sa_kolejne_i_dwucyfrowe():
    kawalki = podziel("\n\n".join(f"Zdanie numer {i}." for i in range(12)))
    assert kawalki[0].id == "s01"
    assert kawalki[-1].id == "s12"


# --- ręczna korekta --------------------------------------------------------


def _trzy():
    return [Kawalek("s01", "Pierwsze."), Kawalek("s02", "Drugie."), Kawalek("s03", "Trzecie.")]


def test_scalanie_laczy_z_nastepnym_i_przenumerowuje():
    wynik = scal(_trzy(), 0)
    assert [k.narracja for k in wynik] == ["Pierwsze. Drugie.", "Trzecie."]
    assert [k.id for k in wynik] == ["s01", "s02"]


def test_scalanie_ostatniego_nie_ma_sensu():
    with pytest.raises(IndexError):
        scal(_trzy(), 2)


def test_rozdzielanie_tnie_na_zdania():
    wynik = rozdziel([Kawalek("s01", "Pierwsze zdanie. Drugie zdanie.")], 0)
    assert [k.narracja for k in wynik] == ["Pierwsze zdanie.", "Drugie zdanie."]


def test_rozdzielanie_pojedynczego_zdania_mowi_dlaczego_sie_nie_da():
    with pytest.raises(ValueError, match="jedno zdanie"):
        rozdziel([Kawalek("s01", "Jedno zdanie.")], 0)

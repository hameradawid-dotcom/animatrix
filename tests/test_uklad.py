"""Testy walidatora układu — pilnują dokładnie tego, co dotąd było zepsute:
elementy nachodzące na siebie i wychodzące poza kadr.
"""

import pytest

from animatrix.formaty import FORMATY, FormatError, opis_kadru, rozdzielczosc, znormalizuj
from animatrix.uklad import Element, Kadr, Prostokat, bledy, podsumowanie, waliduj


def el(nazwa, x0, y0, x1, y1, **kw):
    return Element(id=nazwa, prostokat=Prostokat(x0, y0, x1, y1), **kw)


# --- formaty ---------------------------------------------------------------


def test_stare_nazwy_formatu_mapuja_sie():
    assert znormalizuj("pion") == "9:16"
    assert znormalizuj("poziom") == "16:9"
    assert znormalizuj(None) == "16:9"


def test_nieznany_format_rzuca():
    with pytest.raises(FormatError, match="Nie znam formatu"):
        znormalizuj("21:9")


def test_render_roboczy_zachowuje_proporcje():
    """Podgląd musi mieć tę samą proporcję co finał — inaczej kłamie o kompozycji."""
    for nazwa, fmt in FORMATY.items():
        for jakosc in ("l", "m", "h"):
            w, h, fps = rozdzielczosc(nazwa, jakosc)
            assert abs(w / h - fmt.proporcja) < 0.01, (nazwa, jakosc)
            assert w % 2 == 0 and h % 2 == 0, "H.264 wymaga wymiarów parzystych"
            assert fps == fmt.fps


def test_opis_kadru_podaje_realne_wymiary():
    pion = opis_kadru("9:16")
    poziom = opis_kadru("16:9")
    assert "4.50" in pion and "1080x1920" in pion
    assert "14.22" in poziom
    assert "zasłania" in pion  # strefa bezpieczna TikToka


# --- geometria -------------------------------------------------------------


def test_pokrycie_liczy_udzial_mniejszego():
    duzy = Prostokat(0, 0, 10, 10)
    maly = Prostokat(0, 0, 1, 1)
    assert maly.pokrycie(duzy) == pytest.approx(1.0)
    assert Prostokat(20, 20, 21, 21).pokrycie(duzy) == 0.0


def test_regiony_dziela_strefe_bezpieczna():
    kadr = Kadr.z_formatu("9:16")
    b = kadr.bezpieczny()
    gora, srodek, dol = kadr.region("gora"), kadr.region("srodek"), kadr.region("dol")
    assert gora.y1 == pytest.approx(b.y1)
    assert dol.y0 == pytest.approx(b.y0)
    assert srodek.y0 < srodek.y1
    assert gora.y0 >= srodek.y1 - 1e-6


def test_strefa_bezpieczna_wezsza_od_kadru_w_pionie():
    kadr = Kadr.z_formatu("9:16")
    assert kadr.bezpieczny().wysokosc < kadr.pelny().wysokosc


# --- walidacja -------------------------------------------------------------


def test_poprawna_kompozycja_przechodzi():
    kadr = Kadr.z_formatu("9:16")
    b = kadr.bezpieczny()
    uchybienia = waliduj(
        [el("tytul", -1.5, b.y1 - 1.0, 1.5, b.y1 - 0.4), el("tresc", -1.5, 0.0, 1.5, 0.8)],
        kadr,
    )
    assert bledy(uchybienia) == []
    assert podsumowanie([]) == "układ bez zastrzeżeń"


def test_element_poza_kadrem_to_blad():
    kadr = Kadr.z_formatu("9:16")
    uchybienia = waliduj([el("szeroki", -5.0, 0.0, 5.0, 1.0)], kadr)
    assert [u.kod for u in bledy(uchybienia)] == ["poza_kadrem"]


def test_element_w_strefie_platformy_to_ostrzezenie_nie_blad():
    kadr = Kadr.z_formatu("9:16")
    gora_kadru = kadr.pelny().y1
    uchybienia = waliduj([el("napis", -1.0, gora_kadru - 0.3, 1.0, gora_kadru - 0.05)], kadr)
    assert bledy(uchybienia) == []
    assert any(u.kod == "poza_strefa" for u in uchybienia)


def test_nachodzace_elementy_to_blad():
    kadr = Kadr.z_formatu("9:16")
    uchybienia = waliduj([el("a", -1.0, 0.0, 1.0, 1.0), el("b", -1.0, 0.5, 1.0, 1.5)], kadr)
    kolizje = [u for u in bledy(uchybienia) if u.kod == "kolizja"]
    assert len(kolizje) == 1
    assert "a + b" == kolizje[0].element


def test_lekkie_musniecie_nie_alarmuje():
    """Bbox to prostokąt opisany na obiekcie — drobne zachodzenie jest normalne."""
    kadr = Kadr.z_formatu("9:16")
    uchybienia = waliduj([el("a", -1.0, 0.0, 1.0, 1.0), el("b", -1.0, 0.97, 1.0, 2.0)], kadr)
    assert [u for u in uchybienia if u.kod == "kolizja"] == []


def test_flaga_moze_nachodzic_wycisza_kolizje():
    kadr = Kadr.z_formatu("9:16")
    uchybienia = waliduj(
        [el("mapa", -1.0, 0.0, 1.0, 1.0, moze_nachodzic=True), el("podpis", -1.0, 0.5, 1.0, 1.5)],
        kadr,
    )
    assert [u for u in uchybienia if u.kod == "kolizja"] == []


def test_za_maly_tekst_daje_ostrzezenie():
    kadr = Kadr.z_formatu("9:16")
    uchybienia = waliduj(
        [el("drobny", -0.5, 0.0, 0.5, 0.05, tekst=True, rozmiar_px=12)], kadr
    )
    assert any(u.kod == "maly_tekst" for u in uchybienia)
    assert bledy(uchybienia) == []


def test_ten_sam_uklad_moze_byc_zly_w_innym_formacie():
    """Sedno problemu: kompozycja pisana pod 16:9 wypada poza kadr w 9:16."""
    szeroki = [el("pasek", -6.0, 0.0, 6.0, 1.0)]
    assert bledy(waliduj(szeroki, Kadr.z_formatu("16:9"))) == []
    assert [u.kod for u in bledy(waliduj(szeroki, Kadr.z_formatu("9:16")))] == ["poza_kadrem"]

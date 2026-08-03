"""Testy warstwy usług i API.

Nie renderują — sprawdzają kontrakt, blokadę zapisu i to, że błąd dziedzinowy
dociera do klienta jako czytelny komunikat, a nie jako 500.
"""

from __future__ import annotations

import threading

import pytest

from animatrix import uslugi
from animatrix.models import ScriptMeta
from animatrix.project import BlokadaZajeta, Project
from animatrix.zadania import Rejestr

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def projekt(projekty):
    proj = Project.create("test-api", ScriptMeta(temat="test", format_wideo="9:16", motyw="misja"))
    uslugi.zapisz_scenariusz(proj, ["Pierwsze zdanie.", "Drugie zdanie."])
    return proj


@pytest.fixture()
def klient(projekt):
    from animatrix.serwer import app

    return TestClient(app)


# --- blokada ---------------------------------------------------------------


def test_blokada_nie_wpuszcza_drugiego_zapisu(projekt):
    wynik = {}

    def probuj():
        try:
            with projekt.blokada(timeout=0.2):
                wynik["udalo"] = True
        except BlokadaZajeta:
            wynik["udalo"] = False

    with projekt.blokada():
        watek = threading.Thread(target=probuj)
        watek.start()
        watek.join(5)
    assert wynik["udalo"] is False


def test_blokada_zwalnia_sie_po_wyjsciu(projekt):
    with projekt.blokada():
        pass
    with projekt.blokada(timeout=0.2):
        pass


# --- usługi ----------------------------------------------------------------


def test_zapisany_scenariusz_tworzy_segmenty(projekt):
    d = uslugi.podsumowanie(projekt)
    assert [s["id"] for s in d["segmenty"]] == ["s01", "s02"]
    assert d["kadr"]["wysokosc_px"] == 1920


def test_skrocenie_scenariusza_kasuje_osierocone_specy(projekt):
    uslugi.zapisz_spec(
        projekt, "s02", szablon_nazwy="licznik_hero", parametry={"wartosc": 7}
    )
    assert projekt.spec_path("s02").exists()
    uslugi.zapisz_scenariusz(projekt, ["Zostaje tylko jedno zdanie."])
    assert not projekt.spec_path("s02").exists()


def test_zapis_specu_odrzuca_zle_parametry(projekt):
    with pytest.raises(Exception):
        uslugi.zapisz_spec(projekt, "s01", szablon_nazwy="slupki", parametry={"pozycje": []})
    assert not projekt.spec_path("s01").exists()


def test_zmiana_formatu_nie_rusza_scen(projekt):
    uslugi.zapisz_spec(projekt, "s01", szablon_nazwy="licznik_hero", parametry={"wartosc": 7})
    przed = projekt.spec_path("s01").read_text(encoding="utf-8")
    uslugi.ustaw_meta(projekt, format_wideo="4:5")
    assert uslugi.podsumowanie(projekt)["format"] == "4:5"
    assert projekt.spec_path("s01").read_text(encoding="utf-8") == przed


def test_nieistniejacy_render_nie_jest_ogloszony(projekt):
    """scenes.yaml pamięta ścieżkę po skasowanym pliku — interfejs nie może
    dostać linku do czegoś, czego nie ma."""
    uslugi.zapisz_spec(projekt, "s01", szablon_nazwy="licznik_hero", parametry={"wartosc": 7})
    stan = projekt.load_scenes()
    stan.get("s01").render_roboczy = "renders/draft/s01.mp4"
    projekt.save_scenes(stan)
    segment = uslugi.podsumowanie(projekt)["segmenty"][0]
    assert segment["render_roboczy"] is None


# --- API -------------------------------------------------------------------


def test_info_wystawia_katalog_szablonow(klient):
    d = klient.get("/api/info").json()
    assert {s["nazwa"] for s in d["szablony"]} >= {"slupki", "licznik_hero"}
    assert all("schemat" in s for s in d["szablony"])


def test_podzial_nie_zapisuje_nic(klient, projekt):
    przed = len(uslugi.podsumowanie(projekt)["segmenty"])
    d = klient.post("/api/podzial", json={"tekst": "Raz. Dwa. Trzy."}).json()
    assert d["segmenty"]
    assert len(uslugi.podsumowanie(projekt)["segmenty"]) == przed


def test_bledne_parametry_to_400_z_powodem(klient):
    r = klient.put(
        "/api/projekty/test-api/sceny/s01",
        json={"szablon": "slupki", "parametry": {"pozycje": []}},
    )
    assert r.status_code == 400
    assert "pozycje" in r.json()["detail"]


def test_nieznany_projekt_to_404(klient):
    assert klient.get("/api/projekty/nie-ma-takiego").status_code == 404


def test_nie_da_sie_wyjsc_poza_katalog_projektu(klient):
    r = klient.get("/api/projekty/test-api/plik/../../../etc/passwd")
    assert r.status_code == 404


# --- zadania ---------------------------------------------------------------


def test_zadanie_raportuje_postep_i_konczy_sie():
    rejestr = Rejestr()
    zdarzenia = []
    zadanie = rejestr.uruchom("test", "p", lambda z: (z.raportuj(postep=0.5), "wynik")[1])
    for zd in zadanie.subskrybuj():
        zdarzenia.append(zd.rodzaj)
    assert zdarzenia[-1] == "koniec"
    assert zadanie.stan == "gotowe"
    assert zadanie.wynik == "wynik"


def test_zadanie_z_wyjatkiem_konczy_sie_bledem():
    rejestr = Rejestr()

    def wybucha(_):
        raise RuntimeError("nie poszło")

    zadanie = rejestr.uruchom("test", "p", wybucha)
    list(zadanie.subskrybuj())
    assert zadanie.stan == "blad"
    assert "nie poszło" in zadanie.blad


def test_subskrypcja_skonczonego_zadania_nie_wisi():
    """Klient, który podłączył się sekundę za późno, musi dostać stan końcowy."""
    rejestr = Rejestr()
    zadanie = rejestr.uruchom("test", "p", lambda z: 1)
    list(zadanie.subskrybuj())
    assert [zd.rodzaj for zd in zadanie.subskrybuj()] == ["koniec"]


def test_anulowanie_ustawia_flage_widoczna_dla_pracy():
    rejestr = Rejestr()
    start = threading.Event()

    def dlugie(z):
        start.set()
        while not z.anulowane:
            pass
        return None

    zadanie = rejestr.uruchom("test", "p", dlugie)
    start.wait(5)
    zadanie.anuluj()
    list(zadanie.subskrybuj())
    assert zadanie.stan == "anulowane"

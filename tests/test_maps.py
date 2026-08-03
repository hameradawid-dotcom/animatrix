import json

import pytest

from explainer.assets.maps import MapError, slug

gpd = pytest.importorskip("geopandas")

GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"nazwa": "Małopolskie"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[19.0, 50.0], [20.0, 50.0], [20.0, 51.0], [19.0, 51.0], [19.0, 50.0]]],
            },
        },
        {
            "type": "Feature",
            "properties": {"nazwa": "Śląskie"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[18.0, 50.0], [19.0, 50.0], [19.0, 51.0], [18.0, 51.0], [18.0, 50.0]]],
            },
        },
    ],
}


def test_slug_normalizuje_polskie_znaki():
    assert slug("Kujawsko-Pomorskie") == "kujawsko-pomorskie"
    assert slug("Świętokrzyskie") == "swietokrzyskie"


def test_generuje_svg_i_sidecar(tmp_path):
    from explainer.assets.maps import generuj_svg

    zrodlo = tmp_path / "w.geojson"
    zrodlo.write_text(json.dumps(GEOJSON), encoding="utf-8")

    svg, meta = generuj_svg(zrodlo, tmp_path / "out" / "poland.svg", kolumna_nazwy="nazwa", uproszczenie_m=0)

    tresc = svg.read_text(encoding="utf-8")
    assert tresc.startswith("<svg")
    assert 'id="malopolskie"' in tresc
    assert 'id="slaskie"' in tresc

    dane = json.loads(meta.read_text(encoding="utf-8"))
    # kolejność w JSON-ie musi odpowiadać kolejności ścieżek w SVG
    assert dane["regiony"] == ["malopolskie", "slaskie"]
    assert tresc.index('id="malopolskie"') < tresc.index('id="slaskie"')


def test_zla_kolumna_daje_czytelny_blad(tmp_path):
    from explainer.assets.maps import generuj_svg

    zrodlo = tmp_path / "w.geojson"
    zrodlo.write_text(json.dumps(GEOJSON), encoding="utf-8")

    with pytest.raises(MapError, match="Brak kolumny"):
        generuj_svg(zrodlo, tmp_path / "o.svg", kolumna_nazwy="nie_ma")

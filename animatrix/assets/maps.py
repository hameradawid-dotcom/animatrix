"""Generator map SVG z danych geoprzestrzennych.

Manim czyta mapy jako SVGMobject, a nie jako geometrię, więc konwersja jest
osobnym krokiem. Obok pliku .svg powstaje .json z nazwami regionów w tej samej
kolejności co ścieżki — to jedyny sposób, żeby w scenie trafić w konkretne
województwo (Manim gubi atrybuty `id` przy imporcie SVG).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

# EPSG:2180 (PUWG 1992) — układ metryczny dla Polski, mapa nie jest rozciągnięta.
CRS_POLSKA = 2180

TRANSLIT = str.maketrans("ąćęłńóśźż", "acelnoszz")


class MapError(RuntimeError):
    pass


def slug(nazwa: str) -> str:
    s = nazwa.strip().lower().translate(TRANSLIT)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def _polygons(geom) -> Iterable:
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type == "MultiPolygon":
        return list(geom.geoms)
    return []


def _ring_to_path(coords, project) -> str:
    punkty = [project(x, y) for x, y in coords]
    if not punkty:
        return ""
    head = f"M {punkty[0][0]:.2f},{punkty[0][1]:.2f}"
    tail = " ".join(f"L {x:.2f},{y:.2f}" for x, y in punkty[1:])
    return f"{head} {tail} Z"


def generuj_svg(
    zrodlo: str | Path,
    wyjscie: Path,
    *,
    kolumna_nazwy: str | None = None,
    szerokosc: int = 1000,
    uproszczenie_m: float = 500.0,
) -> tuple[Path, Path]:
    """Zamienia warstwę geo (GeoJSON / shapefile / URL) na SVG + sidecar JSON.

    Zwraca (ścieżka_svg, ścieżka_json).
    """
    try:
        import geopandas as gpd
    except ImportError as exc:  # pragma: no cover - zależy od instalacji użytkownika
        raise MapError(
            "Brak geopandas. Zainstaluj: pip install 'geopandas>=1.0' 'shapely>=2.0'"
        ) from exc

    gdf = gpd.read_file(str(zrodlo))
    if gdf.empty:
        raise MapError(f"Warstwa {zrodlo} jest pusta.")

    if kolumna_nazwy is None:
        kandydaci = [c for c in gdf.columns if c.lower() in ("name", "nazwa", "jpt_nazwa_", "region", "woj")]
        if not kandydaci:
            raise MapError(
                "Nie wiem, która kolumna zawiera nazwę regionu. Podaj --kolumna. "
                f"Dostępne: {', '.join(map(str, gdf.columns))}"
            )
        kolumna_nazwy = kandydaci[0]
    if kolumna_nazwy not in gdf.columns:
        raise MapError(f"Brak kolumny '{kolumna_nazwy}'. Dostępne: {', '.join(map(str, gdf.columns))}")

    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    gdf = gdf.to_crs(CRS_POLSKA)
    if uproszczenie_m > 0:
        gdf["geometry"] = gdf.geometry.simplify(uproszczenie_m, preserve_topology=True)

    minx, miny, maxx, maxy = gdf.total_bounds
    span_x = maxx - minx or 1.0
    span_y = maxy - miny or 1.0
    skala = szerokosc / span_x
    wysokosc = int(span_y * skala)

    def project(x: float, y: float) -> tuple[float, float]:
        return ((x - minx) * skala, (maxy - y) * skala)

    sciezki: list[str] = []
    nazwy: list[str] = []
    gdf = gdf.sort_values(kolumna_nazwy).reset_index(drop=True)

    for _, row in gdf.iterrows():
        d_parts = []
        for poly in _polygons(row.geometry):
            d_parts.append(_ring_to_path(list(poly.exterior.coords), project))
            for wnetrze in poly.interiors:
                d_parts.append(_ring_to_path(list(wnetrze.coords), project))
        d = " ".join(p for p in d_parts if p)
        if not d:
            continue
        nazwa = slug(str(row[kolumna_nazwy]))
        nazwy.append(nazwa)
        sciezki.append(
            f'  <path id="{nazwa}" d="{d}" fill="#1E2632" stroke="#8B96A8" stroke-width="1.5"/>'
        )

    if not sciezki:
        raise MapError("Nie udało się zbudować żadnej ścieżki — sprawdź geometrię warstwy.")

    svg = "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {szerokosc} {wysokosc}" '
            f'width="{szerokosc}" height="{wysokosc}">',
            *sciezki,
            "</svg>",
            "",
        ]
    )

    wyjscie = Path(wyjscie)
    wyjscie.parent.mkdir(parents=True, exist_ok=True)
    wyjscie.write_text(svg, encoding="utf-8")

    meta_path = wyjscie.with_suffix(".json")
    meta_path.write_text(
        json.dumps(
            {"zrodlo": str(zrodlo), "kolumna": kolumna_nazwy, "regiony": nazwy},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return wyjscie, meta_path

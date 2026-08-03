"""HTTP API interfejsu.

Cała logika siedzi w `animatrix.uslugi` — tutaj jest tylko warstwa transportowa.
Dzięki temu CLI i interfejs robią dokładnie to samo, a nie dwie podobne rzeczy,
które z czasem się rozjeżdżają.

Serwer jest LOKALNY: nasłuchuje na 127.0.0.1, nie ma uwierzytelniania i nie
powinien nigdy stać publicznie — daje dostęp do plików projektu i uruchamia
procesy renderu.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from animatrix import formaty, uslugi
from animatrix.config import settings
from animatrix.models import ScriptMeta
from animatrix.project import BlokadaZajeta, Project, ProjectError, dostepne_motywy
from animatrix.zadania import REJESTR

STATYKA = Path(__file__).resolve().parent / "web"

app = FastAPI(title="animatrix", docs_url="/api/docs", openapi_url="/api/openapi.json")


def _projekt(nazwa: str) -> Project:
    try:
        return uslugi.otworz(nazwa)
    except uslugi.UslugaError as exc:
        raise HTTPException(404, str(exc)) from exc


def _opakuj(fn, *args, **kwargs):
    """Błędy dziedzinowe to 400, nie 500 — użytkownik ma zobaczyć powód."""
    try:
        return fn(*args, **kwargs)
    except BlokadaZajeta as exc:
        raise HTTPException(409, str(exc)) from exc
    except (uslugi.UslugaError, ProjectError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


# --------------------------------------------------------------------------
# Metadane narzędzia
# --------------------------------------------------------------------------
@app.get("/api/info")
def info() -> dict[str, Any]:
    cfg = settings()
    return {
        "formaty": [
            {
                "nazwa": f.nazwa,
                "szerokosc": f.szerokosc,
                "wysokosc": f.wysokosc,
                "opis": f.opis,
                "strefa": f.strefa,
            }
            for f in formaty.FORMATY.values()
        ],
        "motywy": dostepne_motywy(),
        "szablony": uslugi.katalog_szablonow(),
        "glos": {
            "silnik": cfg.tts_provider,
            "gotowy": cfg.has_elevenlabs,
        },
        "model_gotowy": cfg.has_anthropic,
    }


# --------------------------------------------------------------------------
# Projekty
# --------------------------------------------------------------------------
class NowyProjekt(BaseModel):
    nazwa: str
    temat: str = ""
    motyw: str = "kh"
    format_wideo: str = "9:16"


@app.get("/api/projekty")
def projekty() -> list[dict[str, Any]]:
    return uslugi.lista_projektow()


@app.post("/api/projekty")
def nowy_projekt(dane: NowyProjekt) -> dict[str, Any]:
    meta = ScriptMeta(
        temat=dane.temat or dane.nazwa,
        motyw=dane.motyw,
        format_wideo=dane.format_wideo,
    )
    proj = _opakuj(Project.create, dane.nazwa, meta)
    return uslugi.podsumowanie(proj)


@app.get("/api/projekty/{nazwa}")
def projekt(nazwa: str) -> dict[str, Any]:
    return _opakuj(uslugi.podsumowanie, _projekt(nazwa))


class ZmianaMeta(BaseModel):
    format_wideo: str | None = None
    motyw: str | None = None


@app.patch("/api/projekty/{nazwa}")
def zmien_meta(nazwa: str, dane: ZmianaMeta) -> dict[str, Any]:
    proj = _projekt(nazwa)
    _opakuj(uslugi.ustaw_meta, proj, format_wideo=dane.format_wideo, motyw=dane.motyw)
    return uslugi.podsumowanie(proj)


# --------------------------------------------------------------------------
# Scenariusz
# --------------------------------------------------------------------------
class Wklejka(BaseModel):
    tekst: str


@app.post("/api/podzial")
def podziel_tekst(dane: Wklejka) -> dict[str, Any]:
    """Podgląd podziału — nic nie zapisuje, użytkownik ma go najpierw poprawić."""
    propozycja = uslugi.zaproponuj_podzial(dane.tekst)
    return {
        "segmenty": propozycja.segmenty,
        "razem_znakow": propozycja.razem_znakow,
        "razem_sekund": propozycja.razem_sekund,
    }


class Scenariusz(BaseModel):
    narracje: list[str] = Field(min_length=1)


@app.put("/api/projekty/{nazwa}/scenariusz")
def zapisz_scenariusz(nazwa: str, dane: Scenariusz) -> dict[str, Any]:
    proj = _projekt(nazwa)
    _opakuj(uslugi.zapisz_scenariusz, proj, dane.narracje)
    return uslugi.podsumowanie(proj)


# --------------------------------------------------------------------------
# Sceny
# --------------------------------------------------------------------------
class SpecWejscie(BaseModel):
    szablon: str
    parametry: dict[str, Any] = Field(default_factory=dict)
    tempo: dict[str, float] = Field(default_factory=dict)
    sekcja: dict[str, Any] | None = None


@app.put("/api/projekty/{nazwa}/sceny/{seg_id}")
def zapisz_scene(nazwa: str, seg_id: str, dane: SpecWejscie) -> dict[str, Any]:
    proj = _projekt(nazwa)
    spec = _opakuj(
        uslugi.zapisz_spec,
        proj,
        seg_id,
        szablon_nazwy=dane.szablon,
        parametry=dane.parametry,
        tempo=dane.tempo,
        sekcja=dane.sekcja,
    )
    return spec.model_dump()


@app.get("/api/projekty/{nazwa}/sceny/{seg_id}/uklad")
def uklad_sceny(nazwa: str, seg_id: str, format: str | None = None) -> dict[str, Any]:
    proj = _projekt(nazwa)
    pomiar = _opakuj(uslugi.sprawdz_scene, proj, seg_id, format_wideo=format)
    return {
        "id": pomiar.id,
        "ok": pomiar.ok,
        "blad": pomiar.blad,
        "takty": pomiar.takty,
        "uchybienia": [
            {"waga": u.waga, "kod": u.kod, "element": u.element, "opis": u.opis}
            for u in pomiar.uchybienia
        ],
        "elementy": [
            {
                "id": e.id,
                "prostokat": [
                    e.prostokat.x0,
                    e.prostokat.y0,
                    e.prostokat.x1,
                    e.prostokat.y1,
                ],
                "tekst": e.tekst,
            }
            for e in pomiar.elementy
        ],
    }


@app.get("/api/projekty/{nazwa}/uklad")
def uklad_projektu(nazwa: str, format: str | None = None) -> dict[str, Any]:
    return _opakuj(uslugi.uchybienia_projektu, _projekt(nazwa), format_wideo=format)


@app.post("/api/projekty/{nazwa}/sceny/{seg_id}/podglad")
def podglad_sceny(nazwa: str, seg_id: str, format: str | None = None) -> dict[str, Any]:
    proj = _projekt(nazwa)
    plik = _opakuj(uslugi.podglad, proj, seg_id, format_wideo=format)
    return {"plik": proj.rel(plik)}


@app.post("/api/projekty/{nazwa}/sceny/{seg_id}/akceptuj")
def akceptuj(nazwa: str, seg_id: str) -> dict[str, str]:
    _opakuj(uslugi.akceptuj_scene, _projekt(nazwa), seg_id)
    return {"stan": "approved"}


# --------------------------------------------------------------------------
# Render i zadania
# --------------------------------------------------------------------------
@app.post("/api/projekty/{nazwa}/sceny/{seg_id}/render")
def renderuj(nazwa: str, seg_id: str, jakosc: str = "l") -> dict[str, Any]:
    zadanie = _opakuj(uslugi.renderuj_scene_w_tle, _projekt(nazwa), seg_id, jakosc=jakosc)
    return zadanie.podsumowanie()


@app.get("/api/zadania")
def zadania(projekt: str | None = None) -> list[dict[str, Any]]:
    return [z.podsumowanie() for z in REJESTR.lista(projekt)]


@app.get("/api/zadania/{zadanie_id}")
def zadanie(zadanie_id: str) -> dict[str, Any]:
    z = REJESTR.pobierz(zadanie_id)
    if z is None:
        raise HTTPException(404, "Nie ma takiego zadania.")
    return z.podsumowanie()


@app.delete("/api/zadania/{zadanie_id}")
def anuluj_zadanie(zadanie_id: str) -> dict[str, Any]:
    z = REJESTR.pobierz(zadanie_id)
    if z is None:
        raise HTTPException(404, "Nie ma takiego zadania.")
    z.anuluj()
    return z.podsumowanie()


@app.get("/api/zadania/{zadanie_id}/strumien")
def strumien(zadanie_id: str) -> StreamingResponse:
    z = REJESTR.pobierz(zadanie_id)
    if z is None:
        raise HTTPException(404, "Nie ma takiego zadania.")

    def zdarzenia():
        for zd in z.subskrybuj():
            yield f"event: {zd.rodzaj}\ndata: {json.dumps(zd.dane, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        zdarzenia(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --------------------------------------------------------------------------
# Pliki projektu (podglądy, rendery)
# --------------------------------------------------------------------------
@app.get("/api/projekty/{nazwa}/plik/{sciezka:path}")
def plik(nazwa: str, sciezka: str) -> FileResponse:
    proj = _projekt(nazwa)
    cel = (proj.root / sciezka).resolve()
    # Bez tego `../../../etc/passwd` wychodzi poza projekt.
    if not cel.is_file() or proj.root.resolve() not in cel.parents:
        raise HTTPException(404, "Nie ma takiego pliku w projekcie.")
    return FileResponse(cel)


# --------------------------------------------------------------------------
# Interfejs
# --------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def strona() -> HTMLResponse:
    index = STATYKA / "index.html"
    if not index.exists():
        return HTMLResponse(
            "<h1>animatrix</h1><p>API działa. Interfejs: <a href='/api/docs'>/api/docs</a></p>"
        )
    return HTMLResponse(index.read_text(encoding="utf-8"))


def uruchom(host: str = "127.0.0.1", port: int = 8760, reload: bool = False) -> None:
    import uvicorn

    uvicorn.run(
        "animatrix.serwer:app" if reload else app,
        host=host,
        port=port,
        reload=reload,
        log_level="warning",
    )

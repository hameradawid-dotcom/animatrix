"""Bezstanowe operacje na projekcie — wspólne dla CLI i interfejsu.

Do tej pory cała logika etapów siedziała wewnątrz funkcji `bramka()`, wymieszana
z promptami `rich`. Nie dało się jej wywołać z API, bo pytała o decyzję przez
`input()`. Tutaj są te same operacje, ale bez interakcji: przyjmują dane,
zwracają dane, rzucają wyjątkiem przy błędzie.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from animatrix import formaty, merge, render, scena as scena_mod, sonda
from animatrix.models import Script, ScriptMeta
from animatrix.podzial import Kawalek, podziel
from animatrix.project import Project, ProjectError
from animatrix.scena import SceneSpec
from animatrix.stages import scenes as stage_scenes
from animatrix.szablony import KATALOG, szablon
from animatrix.szablony.odtwarzacz import ZMIENNA_SPECU
from animatrix.uklad import Kadr, Uchybienie, bledy
from animatrix.zadania import REJESTR, Zadanie


class UslugaError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# Projekt
# --------------------------------------------------------------------------
def otworz(nazwa: str) -> Project:
    try:
        return Project.open(nazwa)
    except ProjectError as exc:
        raise UslugaError(str(exc)) from exc


def lista_projektow() -> list[dict[str, Any]]:
    wynik = []
    for nazwa in Project.list_all():
        proj = Project.open(nazwa)
        try:
            script = proj.load_script()
        except ProjectError:
            continue
        wynik.append(
            {
                "nazwa": nazwa,
                "temat": script.meta.temat,
                "format": script.meta.format_wideo,
                "motyw": script.meta.motyw,
                "segmentow": len(script.segmenty),
            }
        )
    return wynik


def _istniejacy(proj: Project, wzgledna: str | None) -> str | None:
    if not wzgledna:
        return None
    return wzgledna if (proj.root / wzgledna).is_file() else None


def podsumowanie(proj: Project) -> dict[str, Any]:
    script = proj.load_script()
    stan = stage_scenes.synchronizuj(proj, script)
    fmt = formaty.format_wideo(script.meta.format_wideo)
    kadr = Kadr.z_formatu(script.meta.format_wideo)
    bezpieczny = kadr.bezpieczny()

    segmenty = []
    for seg in script.segmenty:
        st = stan.get(seg.id)
        spec = None
        if st is not None and st.spec:
            try:
                spec = scena_mod.wczytaj(proj.root / st.spec)
            except Exception as exc:  # niepoprawny YAML nie może wywalić listy
                spec = None
                segmenty.append(
                    {
                        "id": seg.id,
                        "narracja": seg.narracja,
                        "szablon": None,
                        "blad_specu": str(exc),
                        "status": "failed",
                    }
                )
                continue
        segmenty.append(
            {
                "id": seg.id,
                "narracja": seg.narracja,
                "status": st.status if st else "pending",
                "szablon": spec.szablon if spec else None,
                "parametry": spec.parametry if spec else {},
                "tempo": spec.tempo if spec else {},
                "sekcja": spec.sekcja.model_dump() if spec and spec.sekcja else None,
                "spec": st.spec if st else None,
                # Ścieżka w scenes.yaml przeżywa skasowanie pliku (renders/ nie
                # idzie do gita), więc interfejs musi dostać tylko to, co
                # naprawdę leży na dysku — inaczej pokazuje zepsuty odtwarzacz.
                "render_roboczy": _istniejacy(proj, st.render_roboczy if st else None),
                "podglad": _istniejacy(proj, f"previews/{seg.id}.png"),
                "nieaktualny": bool(st and spec and st.hash_renderu != spec.hash()),
            }
        )

    return {
        "nazwa": proj.name,
        "temat": script.meta.temat,
        "motyw": script.meta.motyw,
        "format": script.meta.format_wideo,
        "kadr": {
            "szerokosc_px": fmt.szerokosc,
            "wysokosc_px": fmt.wysokosc,
            "strefa_bezpieczna": asdict(fmt.strefa_bezpieczna()),
            "bezpieczny_ulamek": {
                "gora": (kadr.pelny().y1 - bezpieczny.y1) / kadr.wysokosc,
                "dol": (bezpieczny.y0 - kadr.pelny().y0) / kadr.wysokosc,
                "lewo": (bezpieczny.x0 - kadr.pelny().x0) / kadr.szerokosc,
                "prawo": (kadr.pelny().x1 - bezpieczny.x1) / kadr.szerokosc,
            },
        },
        "segmenty": segmenty,
        "koszty": proj.load_costs().model_dump(),
    }


def ustaw_meta(proj: Project, *, format_wideo: str | None = None, motyw: str | None = None) -> None:
    """Zmiana formatu nie wymaga przepisywania scen — szablony pozycjonują
    względem kadru, nie względem współrzędnych."""
    with proj.blokada():
        script = proj.load_script()
        if format_wideo:
            script.meta.format_wideo = formaty.znormalizuj(format_wideo)
        if motyw:
            proj.install_runtime(motyw, force=True)
            script.meta.motyw = motyw
        proj.save_script(script)


# --------------------------------------------------------------------------
# Scenariusz
# --------------------------------------------------------------------------
@dataclass
class PropozycjaPodzialu:
    segmenty: list[dict[str, Any]]
    razem_znakow: int
    razem_sekund: float


def zaproponuj_podzial(tekst: str) -> PropozycjaPodzialu:
    kawalki = podziel(tekst)
    return PropozycjaPodzialu(
        segmenty=[
            {"id": k.id, "narracja": k.narracja, "znakow": k.znakow, "sekundy": round(k.sekundy, 1)}
            for k in kawalki
        ],
        razem_znakow=sum(k.znakow for k in kawalki),
        razem_sekund=round(sum(k.sekundy for k in kawalki), 1),
    )


def zapisz_scenariusz(proj: Project, narracje: list[str], *, zatwierdz: bool = True) -> Script:
    """Nadpisuje scenariusz listą narracji. Sceny bez odpowiednika znikają."""
    narracje = [n.strip() for n in narracje if n.strip()]
    if not narracje:
        raise UslugaError("Pusty scenariusz — nie ma czego zapisać.")

    with proj.blokada():
        script = proj.load_script()
        stare = {s.id: s for s in script.segmenty}
        kawalki = [Kawalek(id=f"s{i + 1:02d}", narracja=n) for i, n in enumerate(narracje)]

        nowe = []
        koszty = proj.load_costs()
        for k in kawalki:
            segment = stare.get(k.id)
            if segment is None:
                from animatrix.models import Segment

                segment = Segment(id=k.id, narracja=k.narracja)
            else:
                segment.narracja = k.narracja
            segment.status = "approved" if zatwierdz else "draft"
            koszty.zapisz_narracje(k.id, k.narracja)
            nowe.append(segment)

        script.segmenty = nowe
        proj.save_script(script)
        proj.save_costs(koszty)

        # Specy segmentów, które wypadły ze scenariusza, tylko myliłyby
        # interfejs — nie ma już czego nimi animować.
        zostaja = {k.id for k in kawalki}
        for plik in sorted(proj.specs_dir.glob("s*.yaml")):
            if plik.stem not in zostaja:
                plik.unlink()
        stage_scenes.synchronizuj(proj, script)
    return script


# --------------------------------------------------------------------------
# Scena
# --------------------------------------------------------------------------
def katalog_szablonow() -> list[dict[str, Any]]:
    return [
        {
            "nazwa": s.nazwa,
            "opis": s.opis,
            "pokrywa": s.pokrywa,
            "przyklad": s.przyklad,
            "schemat": s.schemat(),
        }
        for s in KATALOG.values()
    ]


def wczytaj_spec(proj: Project, seg_id: str) -> SceneSpec | None:
    sciezka = proj.spec_path(seg_id)
    if not sciezka.exists():
        return None
    return scena_mod.wczytaj(sciezka)


def zapisz_spec(
    proj: Project,
    seg_id: str,
    *,
    szablon_nazwy: str,
    parametry: dict[str, Any],
    tempo: dict[str, float] | None = None,
    sekcja: dict[str, Any] | None = None,
) -> SceneSpec:
    """Waliduje i zapisuje spec. Rzuca zanim cokolwiek trafi na dysk."""
    script = proj.load_script()
    segment = script.get(seg_id)
    if segment is None:
        raise UslugaError(f"Scenariusz nie ma segmentu {seg_id}.")

    if szablon_nazwy != scena_mod.SZABLON_KOD:
        szablon(szablon_nazwy).Parametry.model_validate(parametry)

    spec = SceneSpec(
        id=seg_id,
        narracja=segment.narracja,
        szablon=szablon_nazwy,
        parametry=parametry,
        tempo=tempo or {},
        sekcja=sekcja,
    )
    with proj.blokada():
        scena_mod.zapisz(spec, proj.spec_path(seg_id))
        stage_scenes.synchronizuj(proj, script)
    return spec


def sprawdz_scene(proj: Project, seg_id: str, *, format_wideo: str | None = None):
    script = proj.load_script()
    fmt = format_wideo or script.meta.format_wideo
    stan = stage_scenes.synchronizuj(proj, script)
    st = stan.get(seg_id)
    if st is None:
        raise UslugaError(f"Nie znam segmentu {seg_id}.")
    plik, klasa, extra = stage_scenes.cel_renderu(proj, st)
    if not plik.exists():
        raise UslugaError(f"Brak pliku sceny dla {seg_id}.")
    pomiar = sonda.zmierz(proj, plik, klasa, format=fmt, extra_env=extra)
    if pomiar.takty:
        with proj.blokada():
            swiezy = proj.load_scenes()
            wpis = swiezy.get(seg_id)
            if wpis is not None:
                wpis.takty = pomiar.takty
                proj.save_scenes(swiezy)
    return pomiar


def _cel(proj: Project, seg_id: str):
    script = proj.load_script()
    stan = stage_scenes.synchronizuj(proj, script)
    st = stan.get(seg_id)
    if st is None:
        raise UslugaError(f"Nie znam segmentu {seg_id}.")
    return script, stan, st, stage_scenes.cel_renderu(proj, st)


def podglad(proj: Project, seg_id: str, *, format_wideo: str | None = None) -> Path:
    """Statyczna klatka końcowa — sekundy, bez audio, do oceny kompozycji."""
    script, _, st, (plik, klasa, extra) = _cel(proj, seg_id)
    fmt = format_wideo or script.meta.format_wideo
    wynik = render.render(
        proj,
        plik,
        klasa,
        quality="m",
        still=True,
        out_name=f"podglad_{seg_id}",
        voice=False,
        format=fmt,
        extra_env=extra,
    )
    if not wynik.ok:
        raise UslugaError(f"Podgląd {seg_id} nie powstał:\n{wynik.tail[-800:]}")
    cel = proj.previews_dir / f"{seg_id}.png"
    return render.copy_output(wynik, cel)


def renderuj_scene_w_tle(proj: Project, seg_id: str, *, jakosc: str = "l") -> Zadanie:
    if REJESTR.aktywne(proj.name):
        raise UslugaError("Ten projekt ma już render w toku. Poczekaj albo go anuluj.")

    script, stan, st, (plik, klasa, extra) = _cel(proj, seg_id)
    fmt = script.meta.format_wideo
    spec = wczytaj_spec(proj, seg_id)

    # Sonda kosztuje ~2 s i daje dwie rzeczy naraz: liczbę taktów (bez niej
    # pasek postępu nie ma mianownika) i uchybienia układu wyłapane ZANIM
    # pójdzie kilkuminutowy render.
    taktow = st.takty
    if taktow is None:
        try:
            taktow = sprawdz_scene(proj, seg_id).takty
        except UslugaError:
            taktow = None

    def praca(zadanie: Zadanie):
        def na_postep(postep: render.Postep) -> None:
            zadanie.raportuj(
                postep=postep.ulamek(taktow),
                komunikat=f"animacja {postep.animacja + 1} — {postep.procent_animacji}%",
            )

        wynik = render.render_strumieniowo(
            proj,
            plik,
            klasa,
            quality=jakosc,
            voice=True,
            format=fmt,
            extra_env=extra,
            na_postep=na_postep,
            anuluj=lambda: zadanie.anulowane,
        )
        if zadanie.anulowane:
            return {"anulowane": True}
        if not wynik.ok:
            raise UslugaError(wynik.tail[-1200:])

        cel = proj.renders_dir / ("draft" if jakosc == "l" else "final") / f"{seg_id}.mp4"
        render.copy_output(wynik, cel)
        with proj.blokada():
            swiezy = proj.load_scenes()
            wpis = swiezy.get(seg_id)
            if wpis is not None:
                if jakosc == "l":
                    wpis.render_roboczy = proj.rel(cel)
                else:
                    wpis.render_final = proj.rel(cel)
                wpis.status = "rendered"
                wpis.ostatni_blad = None
                if spec is not None:
                    wpis.hash_renderu = spec.hash()
                proj.save_scenes(swiezy)
        return {"plik": proj.rel(cel), "sekundy": merge.duration(cel)}

    return REJESTR.uruchom(f"render {seg_id}", proj.name, praca)


def akceptuj_scene(proj: Project, seg_id: str) -> None:
    with proj.blokada():
        stan = proj.load_scenes()
        st = stan.get(seg_id)
        if st is None:
            raise UslugaError(f"Nie znam segmentu {seg_id}.")
        st.status = "approved"
        proj.save_scenes(stan)


def uchybienia_projektu(proj: Project, *, format_wideo: str | None = None) -> dict[str, Any]:
    wyniki = sonda.zmierz_projekt(proj, format=format_wideo)
    return {
        "sceny": [
            {
                "id": w.id,
                "ok": w.ok,
                "blad": w.blad,
                "takty": w.takty,
                "uchybienia": [
                    {"waga": u.waga, "kod": u.kod, "element": u.element, "opis": u.opis}
                    for u in w.uchybienia
                ],
            }
            for w in wyniki
        ],
        "bledow": sum(len(bledy(w.uchybienia)) for w in wyniki) + sum(1 for w in wyniki if w.blad),
    }


__all__ = [
    "PropozycjaPodzialu",
    "Uchybienie",
    "UslugaError",
    "ZMIENNA_SPECU",
    "ScriptMeta",
    "akceptuj_scene",
    "katalog_szablonow",
    "lista_projektow",
    "otworz",
    "podglad",
    "podsumowanie",
    "renderuj_scene_w_tle",
    "sprawdz_scene",
    "uchybienia_projektu",
    "ustaw_meta",
    "wczytaj_spec",
    "zaproponuj_podzial",
    "zapisz_scenariusz",
    "zapisz_spec",
]

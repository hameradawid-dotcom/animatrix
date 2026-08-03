from __future__ import annotations

from pathlib import Path

from animatrix import merge, prompts, render, ui
from animatrix.llm import LLM, LLMError
from animatrix.models import SceneState, Scenes, Script, Storyboard, scene_class_name
from animatrix.project import Project
from animatrix.stages.common import (
    dopisz_uwage,
    dostepne_assety,
    make_llm,
    teksty_uwag,
    zapisz_kod,
)

ETAP = "scene"
MAX_PROB_NAPRAWY = 3


def _wymagaj_storyboardu(project: Project) -> tuple[Script, Storyboard]:
    script = project.load_script()
    sb = project.load_storyboard()
    if not script.approved:
        raise RuntimeError("Etap 3 wymaga zaakceptowanego scenariusza (`animatrix script`).")
    if not sb.approved or len(sb.segmenty) != len(script.segmenty):
        raise RuntimeError("Etap 3 wymaga zaakceptowanego storyboardu (`animatrix storyboard`).")
    return script, sb


def synchronizuj(project: Project, script: Script) -> Scenes:
    """Dokłada wpisy dla nowych segmentów, zachowując stan istniejących."""
    stan = project.load_scenes()
    istniejace = {s.id: s for s in stan.segmenty}
    stan.segmenty = [
        istniejace.get(
            seg.id,
            SceneState(
                id=seg.id,
                klasa=scene_class_name(seg.id),
                plik=f"scenes/{seg.id}.py",
            ),
        )
        for seg in script.segmenty
    ]
    project.save_scenes(stan)
    return stan


def sciezka_kodu(project: Project, st: SceneState) -> Path:
    return project.root / st.plik


def format_wideo(project: Project) -> str:
    return project.load_script().meta.format_wideo


def _generuj_kod(project: Project, llm: LLM, script: Script, sb: Storyboard, st: SceneState) -> str:
    seg = script.get(st.id)
    item = sb.get(st.id)
    if seg is None or item is None:
        raise RuntimeError(f"Brak scenariusza albo storyboardu dla segmentu {st.id}.")

    system = prompts.scene_system(st.klasa, script.meta.motyw)
    user = prompts.scene_user(
        temat=script.meta.temat,
        segment_id=st.id,
        klasa=st.klasa,
        narracja=seg.narracja,
        opis_wizualny=item.opis_wizualny,
        obiekty=item.obiekty,
        animacje=item.animacje,
        assety=item.assety,
        dostepne_assety=dostepne_assety(project),
        uwagi=teksty_uwag(st.uwagi),
    )
    with ui.console.status(f"{st.id}: model pisze scenę…"):
        kod = llm.code_call(system, user)
    zapisz_kod(sciezka_kodu(project, st), kod)
    return kod


def renderuj_z_naprawa(
    project: Project,
    llm: LLM,
    st: SceneState,
    stan: Scenes,
    *,
    max_prob: int = MAX_PROB_NAPRAWY,
) -> bool:
    """Render roboczy (-ql, z audio) z pętlą samonaprawy. Zwraca True przy sukcesie."""
    plik = sciezka_kodu(project, st)
    kod = plik.read_text(encoding="utf-8")
    proba = 0

    while True:
        with ui.console.status(f"{st.id}: render roboczy…"):
            wynik = render.render(
                project, plik, st.klasa, quality="l", voice=True, format=format_wideo(project)
            )

        if wynik.ok:
            cel = project.renders_dir / "draft" / f"{st.id}.mp4"
            render.copy_output(wynik, cel)
            st.render_roboczy = project.rel(cel)
            st.status = "rendered"
            st.ostatni_blad = None
            st.proby_naprawy = proba
            project.save_scenes(stan)
            czas = merge.duration(cel)
            ui.ok(f"{st.id}: render OK" + (f" ({czas:.1f} s)" if czas else ""))
            return True

        if proba >= max_prob:
            st.status = "failed"
            st.ostatni_blad = wynik.tail
            st.proby_naprawy = proba
            project.save_scenes(stan)
            ui.blad(f"{st.id}: render nie działa po {max_prob} próbach naprawy.")
            ui.console.print(f"[dim]{wynik.tail[-1500:]}[/dim]")
            ui.info(f"Kod sceny: {plik}")
            return False

        proba += 1
        ui.warn(f"{st.id}: render padł — próba naprawy {proba}/{max_prob}")
        try:
            with ui.console.status(f"{st.id}: model naprawia kod…"):
                kod = llm.code_call(
                    prompts.FIX_SYSTEM,
                    prompts.fix_user(klasa=st.klasa, kod=kod, blad=wynik.tail, proba=proba),
                )
            zapisz_kod(plik, kod)
        except LLMError as exc:
            st.status = "failed"
            st.ostatni_blad = f"{wynik.tail}\n\n[naprawa nieudana] {exc}"
            st.proby_naprawy = proba
            project.save_scenes(stan)
            ui.blad(str(exc))
            return False


def popraw_z_uwaga(
    project: Project,
    llm: LLM,
    st: SceneState,
    stan: Scenes,
    uwaga: str,
) -> bool:
    dopisz_uwage(st.uwagi, ETAP, uwaga)
    plik = sciezka_kodu(project, st)
    kod = plik.read_text(encoding="utf-8")
    with ui.console.status(f"{st.id}: model poprawia scenę…"):
        nowy = llm.code_call(
            prompts.TWEAK_SYSTEM,
            prompts.tweak_user(klasa=st.klasa, kod=kod, uwagi=teksty_uwag(st.uwagi)),
        )
    zapisz_kod(plik, nowy)
    st.status = "generated"
    project.save_scenes(stan)
    return renderuj_z_naprawa(project, llm, st, stan)


def bramka(project: Project, *, tylko: str | None = None, max_prob: int = MAX_PROB_NAPRAWY) -> bool:
    llm = make_llm(project)
    script, sb = _wymagaj_storyboardu(project)
    stan = synchronizuj(project, script)

    ui.naglowek("Etap 3 — sceny")

    i = 0
    while i < len(stan.segmenty):
        st = stan.segmenty[i]
        if tylko and st.id != tylko:
            i += 1
            continue
        if st.status == "approved" and not tylko:
            i += 1
            continue

        if st.status in ("pending", "failed") or not sciezka_kodu(project, st).exists():
            try:
                _generuj_kod(project, llm, script, sb, st)
            except (LLMError, RuntimeError) as exc:
                ui.blad(f"{st.id}: {exc}")
                i += 1
                continue
            st.status = "generated"
            st.proby_naprawy = 0
            project.save_scenes(stan)

        if st.status == "generated":
            if not renderuj_z_naprawa(project, llm, st, stan, max_prob=max_prob):
                wybor = ui.wybor(
                    f"{st.id} nie chce się wyrenderować",
                    {"e": "edytuj kod ręcznie", "n": "napraw z uwagą", "p": "pomiń", "q": "wyjdź"},
                    "p",
                )
                if wybor == "q":
                    return False
                if wybor == "p":
                    i += 1
                    continue
                if wybor == "e":
                    plik = sciezka_kodu(project, st)
                    nowy = ui.edytuj(plik.read_text(encoding="utf-8"), suffix=".py")
                    if nowy:
                        zapisz_kod(plik, nowy)
                    st.status = "generated"
                    project.save_scenes(stan)
                    continue
                if wybor == "n":
                    uwaga = ui.zapytaj("Podpowiedź dla modelu")
                    if uwaga.strip():
                        dopisz_uwage(st.uwagi, ETAP, uwaga.strip())
                        st.status = "pending"
                        project.save_scenes(stan)
                    continue

        podglad = project.root / st.render_roboczy if st.render_roboczy else None
        tresc = f"kod: {st.plik}\nrender roboczy: {st.render_roboczy or '—'}"
        if st.uwagi:
            tresc += "\nuwagi: " + " | ".join(teksty_uwag(st.uwagi))
        seg = script.get(st.id)
        ui.panel_segmentu(st.id, st.status, tresc, f"— {ui.skrot(seg.narracja if seg else '', 45)}")
        if podglad and podglad.exists():
            ui.info(f"Obejrzyj: {podglad}")

        wybor = ui.wybor(
            "Decyzja",
            {
                "a": "akceptuj",
                "r": "poprawka z uwagą",
                "e": "edytuj kod ręcznie",
                "o": "otwórz render",
                "p": "pomiń",
                "q": "wyjdź",
            },
            "a",
        )
        if wybor == "q":
            return False
        if wybor == "o":
            if podglad and podglad.exists():
                ui.otworz(podglad)
            else:
                ui.warn("Brak renderu roboczego.")
            continue
        if wybor == "p":
            i += 1
            continue
        if wybor == "a":
            st.status = "approved"
            project.save_scenes(stan)
            i += 1
            continue
        if wybor == "r":
            uwaga = ui.zapytaj("Co poprawić")
            if not uwaga.strip():
                continue
            try:
                popraw_z_uwaga(project, llm, st, stan, uwaga.strip())
            except LLMError as exc:
                ui.blad(str(exc))
            continue
        if wybor == "e":
            plik = sciezka_kodu(project, st)
            nowy = ui.edytuj(plik.read_text(encoding="utf-8"), suffix=".py")
            if nowy:
                zapisz_kod(plik, nowy)
                st.status = "generated"
                project.save_scenes(stan)
                renderuj_z_naprawa(project, llm, st, stan, max_prob=max_prob)
            continue

    zatwierdzone = sum(1 for s in stan.segmenty if s.status == "approved")
    if stan.approved:
        ui.ok(f"Wszystkie sceny zatwierdzone ({zatwierdzone}/{len(stan.segmenty)}).")
        return True
    ui.warn(f"Zatwierdzone {zatwierdzone}/{len(stan.segmenty)} scen. Finalny render wymaga kompletu.")
    return False


def render_finalny(project: Project, *, jakosc: str = "h", tylko_scal: bool = False) -> Path:
    script = project.load_script()
    stan = project.load_scenes()
    if not stan.approved or len(stan.segmenty) != len(script.segmenty):
        raise RuntimeError(
            "Finalny render wymaga zatwierdzenia wszystkich scen. Uruchom `animatrix scenes`."
        )

    ui.naglowek(f"Render finalny ({'4K' if jakosc == 'k' else '1080p'})")
    katalog = project.renders_dir / ("final4k" if jakosc == "k" else "final")
    pliki: list[Path] = []

    for st in stan.segmenty:
        cel = katalog / f"{st.id}.mp4"
        if tylko_scal or (cel.exists() and st.render_final == project.rel(cel)):
            if not cel.exists():
                raise RuntimeError(f"Brak renderu finalnego dla {st.id}: {cel}")
            ui.info(f"{st.id}: używam istniejącego renderu")
            pliki.append(cel)
            continue

        with ui.console.status(f"{st.id}: render finalny…"):
            wynik = render.render(
                project,
                sciezka_kodu(project, st),
                st.klasa,
                quality=jakosc,
                voice=True,
                format=script.meta.format_wideo,
                timeout=7200,
            )
        if not wynik.ok:
            ui.console.print(f"[dim]{wynik.tail[-1500:]}[/dim]")
            raise RuntimeError(
                f"{st.id}: render finalny padł, mimo że render roboczy przechodził. "
                "Sprawdź scenę i uruchom `animatrix scenes --segment " + st.id + "`."
            )
        render.copy_output(wynik, cel)
        st.render_final = project.rel(cel)
        project.save_scenes(stan)
        ui.ok(f"{st.id}: gotowe")
        pliki.append(cel)

    wyjscie = project.output_dir / ("final_4k.mp4" if jakosc == "k" else "final.mp4")
    with ui.console.status("scalam sceny ffmpeg-iem…"):
        merge.concat(pliki, wyjscie, workdir=project.renders_dir)

    czas = merge.duration(wyjscie)
    ui.ok(f"Gotowe: {wyjscie}" + (f"  ({czas:.1f} s)" if czas else ""))
    return wyjscie

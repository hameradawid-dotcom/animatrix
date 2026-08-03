from __future__ import annotations

from pathlib import Path

from animatrix import prompts, render, ui
from animatrix.llm import LLM, LLMError
from animatrix.models import Script, Storyboard, StoryboardItem
from animatrix.project import Project
from animatrix.stages.common import (
    dopisz_uwage,
    dostepne_assety,
    make_llm,
    teksty_uwag,
    zapisz_kod,
)

ETAP = "storyboard"
PROBY_PODGLADU = 2


def klasa_podgladu(seg_id: str) -> str:
    return "Podglad_" + "".join(ch for ch in seg_id.upper() if ch.isalnum())


def _wymagaj_scenariusza(project: Project) -> Script:
    script = project.load_script()
    if not script.approved:
        raise RuntimeError(
            "Etap 2 wymaga zaakceptowanego scenariusza. Uruchom najpierw `animatrix script`."
        )
    return script


def generuj(project: Project, llm: LLM, script: Script) -> Storyboard:
    ui.info("Generuję storyboard dla wszystkich segmentów…")
    with ui.console.status("model dobiera warstwę wizualną…"):
        data = llm.json_call(
            prompts.storyboard_system(script.meta.motyw, script.meta.format_wideo),
            prompts.storyboard_user(
                temat=script.meta.temat,
                segmenty=[(s.id, s.narracja) for s in script.segmenty],
            ),
            prompts.STORYBOARD_SCHEMA,
        )

    po_id = {str(d.get("id")): d for d in data.get("segmenty", [])}
    sb = project.load_storyboard()
    istniejace = {i.id: i for i in sb.segmenty}

    pozycje: list[StoryboardItem] = []
    for seg in script.segmenty:
        stary = istniejace.get(seg.id)
        if stary is not None and stary.status == "approved":
            pozycje.append(stary)
            continue
        d = po_id.get(seg.id)
        if d is None:
            raise LLMError(f"Model nie zwrócił storyboardu dla segmentu {seg.id}.")
        pozycje.append(
            StoryboardItem(
                id=seg.id,
                opis_wizualny=str(d["opis_wizualny"]).strip(),
                obiekty=[str(x) for x in d.get("obiekty", [])],
                animacje=[str(x) for x in d.get("animacje", [])],
                assety=[str(x) for x in d.get("assety", [])],
                uwagi=stary.uwagi if stary else [],
            )
        )

    sb.segmenty = pozycje
    project.save_storyboard(sb)
    ui.ok(f"Storyboard: {len(pozycje)} kadrów")
    return sb


def regeneruj_pozycje(
    project: Project,
    llm: LLM,
    script: Script,
    sb: Storyboard,
    item: StoryboardItem,
    uwaga: str,
) -> StoryboardItem:
    dopisz_uwage(item.uwagi, ETAP, uwaga)
    seg = script.get(item.id)
    idx = sb.segmenty.index(item)
    sasiedzi = "\n".join(
        f"{sb.segmenty[j].id}: {sb.segmenty[j].opis_wizualny}"
        for j in (idx - 1, idx + 1)
        if 0 <= j < len(sb.segmenty)
    )

    with ui.console.status("model szuka innego pomysłu…"):
        data = llm.json_call(
            prompts.storyboard_system(script.meta.motyw, script.meta.format_wideo),
            prompts.storyboard_regen_user(
                temat=script.meta.temat,
                segment_id=item.id,
                narracja=seg.narracja if seg else "",
                obecny_opis=item.opis_wizualny,
                sasiedzi=sasiedzi,
                uwagi=teksty_uwag(item.uwagi),
            ),
            prompts.STORYBOARD_ONE_SCHEMA,
        )

    item.opis_wizualny = str(data["opis_wizualny"]).strip()
    item.obiekty = [str(x) for x in data.get("obiekty", [])]
    item.animacje = [str(x) for x in data.get("animacje", [])]
    item.assety = [str(x) for x in data.get("assety", [])]
    item.status = "draft"
    item.podglad = None
    project.save_storyboard(sb)
    return item


def zbuduj_podglad(
    project: Project,
    llm: LLM,
    script: Script,
    item: StoryboardItem,
) -> Path | None:
    """Generuje kod statycznej klatki i renderuje ją w niskiej jakości bez audio."""
    seg = script.get(item.id)
    klasa = klasa_podgladu(item.id)
    plik = project.previews_dir / "_src" / f"{item.id}.py"

    system = prompts.preview_system(klasa, script.meta.motyw, script.meta.format_wideo)
    user = prompts.preview_user(
        segment_id=item.id,
        klasa=klasa,
        narracja=seg.narracja if seg else "",
        opis_wizualny=item.opis_wizualny,
        obiekty=item.obiekty,
        dostepne_assety=dostepne_assety(project),
    )

    with ui.console.status(f"{item.id}: generuję klatkę podglądową…"):
        kod = llm.code_call(system, user, max_tokens=16000)
    zapisz_kod(plik, kod)

    for proba in range(1, PROBY_PODGLADU + 1):
        wynik = render.render(
            project,
            plik,
            klasa,
            quality="l",
            still=True,
            out_name=f"podglad_{item.id}",
            voice=False,
            format=script.meta.format_wideo,
            timeout=600,
        )
        if wynik.ok:
            cel = project.previews_dir / f"{item.id}.png"
            render.copy_output(wynik, cel)
            item.podglad = project.rel(cel)
            return cel

        if proba == PROBY_PODGLADU:
            ui.warn(f"{item.id}: klatka podglądowa się nie wyrenderowała — oceniaj po opisie.")
            ui.console.print(f"[dim]{wynik.tail[-600:]}[/dim]")
            return None

        ui.warn(f"{item.id}: render podglądu padł, próba naprawy {proba}/{PROBY_PODGLADU - 1}")
        try:
            with ui.console.status("model poprawia kod podglądu…"):
                kod = llm.code_call(
                    prompts.FIX_SYSTEM,
                    prompts.fix_user(klasa=klasa, kod=kod, blad=wynik.tail, proba=proba),
                    max_tokens=16000,
                )
            zapisz_kod(plik, kod)
        except LLMError as exc:
            ui.blad(str(exc))
            return None
    return None


def bramka(project: Project, *, tylko: str | None = None, bez_podgladow: bool = False) -> bool:
    llm = make_llm(project)
    script = _wymagaj_scenariusza(project)
    sb = project.load_storyboard()
    if len(sb.segmenty) != len(script.segmenty):
        sb = generuj(project, llm, script)

    ui.naglowek("Etap 2 — storyboard")

    i = 0
    while i < len(sb.segmenty):
        item = sb.segmenty[i]
        if tylko and item.id != tylko:
            i += 1
            continue
        if item.status == "approved" and not tylko:
            i += 1
            continue

        seg = script.get(item.id)
        if not bez_podgladow and item.podglad is None:
            zbuduj_podglad(project, llm, script, item)
            project.save_storyboard(sb)

        tresc = item.opis_wizualny
        if item.obiekty:
            tresc += "\n\n[dim]obiekty:[/dim] " + ", ".join(item.obiekty)
        if item.animacje:
            tresc += "\n[dim]animacje:[/dim] " + ", ".join(item.animacje)
        if item.assety:
            tresc += "\n[dim]assety:[/dim] " + ", ".join(item.assety)
        if item.podglad:
            tresc += f"\n[dim]podgląd:[/dim] {project.root / item.podglad}"

        ui.panel_segmentu(item.id, item.status, tresc, f"— {ui.skrot(seg.narracja if seg else '', 45)}")

        wybor = ui.wybor(
            "Decyzja",
            {
                "a": "akceptuj",
                "e": "edytuj opis",
                "r": "inny pomysł (z uwagą)",
                "o": "otwórz podgląd",
                "p": "pomiń",
                "q": "wyjdź",
            },
            "a",
        )
        if wybor == "q":
            project.save_storyboard(sb)
            return False
        if wybor == "o":
            if item.podglad:
                ui.otworz(project.root / item.podglad)
            else:
                ui.warn("Brak klatki podglądowej dla tego segmentu.")
            continue
        if wybor == "p":
            i += 1
            continue
        if wybor == "a":
            item.status = "approved"
            project.save_storyboard(sb)
            i += 1
            continue
        if wybor == "e":
            nowy = ui.edytuj(item.opis_wizualny, suffix=".md")
            if nowy:
                item.opis_wizualny = nowy
                item.status = "approved"
                item.podglad = None
                project.save_storyboard(sb)
                ui.ok(f"{item.id} zaktualizowany i zaakceptowany")
            i += 1
            continue
        if wybor == "r":
            uwaga = ui.zapytaj("Co poprawić / czego unikać")
            if not uwaga.strip():
                ui.warn("Pusta uwaga — pomijam regenerację.")
                continue
            try:
                regeneruj_pozycje(project, llm, script, sb, item, uwaga.strip())
            except LLMError as exc:
                ui.blad(str(exc))
            continue

    project.save_storyboard(sb)
    zatwierdzone = sum(1 for s in sb.segmenty if s.status == "approved")
    if sb.approved:
        ui.ok(f"Storyboard zatwierdzony w całości ({zatwierdzone}/{len(sb.segmenty)}).")
        return True
    ui.warn(f"Zatwierdzone {zatwierdzone}/{len(sb.segmenty)} kadrów. Etap 3 wymaga kompletu.")
    return False

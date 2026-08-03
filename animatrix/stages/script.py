from __future__ import annotations

from animatrix import prompts, ui
from animatrix.llm import LLM, LLMError
from animatrix.models import Script, Segment
from animatrix.project import Project
from animatrix.stages.common import dopisz_uwage, make_llm, segment_id, teksty_uwag

ETAP = "script"


def generuj(project: Project, llm: LLM) -> Script:
    script = project.load_script()
    meta = script.meta
    ui.info(f"Generuję scenariusz: {meta.temat} ({meta.docelowa_dlugosc_s} s)")
    with ui.console.status("model pisze scenariusz…"):
        data = llm.json_call(
            prompts.SCRIPT_SYSTEM,
            prompts.script_user(
                temat=meta.temat,
                grupa_docelowa=meta.grupa_docelowa,
                dlugosc_s=meta.docelowa_dlugosc_s,
                ton=meta.ton,
                kluczowe_punkty=meta.kluczowe_punkty,
            ),
            prompts.SCRIPT_SCHEMA,
        )

    segmenty = [
        Segment(id=segment_id(i), narracja=" ".join(str(d["narracja"]).split()))
        for i, d in enumerate(data.get("segmenty", []))
        if str(d.get("narracja", "")).strip()
    ]
    if not segmenty:
        raise LLMError("Model nie zwrócił żadnego segmentu.")

    script.segmenty = segmenty
    project.save_script(script)
    ui.ok(f"Scenariusz: {len(segmenty)} segmentów, {suma_znakow(script)} znaków narracji")
    return script


def regeneruj_segment(project: Project, llm: LLM, script: Script, seg: Segment, uwaga: str) -> Segment:
    dopisz_uwage(seg.uwagi, ETAP, uwaga)
    idx = script.segmenty.index(seg)
    przed = script.segmenty[idx - 1].narracja if idx > 0 else ""
    po = script.segmenty[idx + 1].narracja if idx + 1 < len(script.segmenty) else ""

    with ui.console.status("model poprawia segment…"):
        data = llm.json_call(
            prompts.SCRIPT_SYSTEM,
            prompts.script_regen_user(
                temat=script.meta.temat,
                segment_id=seg.id,
                narracja=seg.narracja,
                kontekst_przed=przed,
                kontekst_po=po,
                uwagi=teksty_uwag(seg.uwagi),
            ),
            prompts.NARRACJA_SCHEMA,
        )
    seg.narracja = " ".join(str(data["narracja"]).split())
    seg.status = "draft"
    project.save_script(script)
    return seg


def suma_znakow(script: Script) -> int:
    return sum(len(s.narracja) for s in script.segmenty)


def szacowana_dlugosc(script: Script, cps: float = 14.5) -> float:
    return suma_znakow(script) / cps


def bramka(project: Project, *, tylko: str | None = None) -> bool:
    """Interaktywna bramka akceptacji. Zwraca True, gdy wszystkie segmenty są approved."""
    llm = make_llm(project)
    script = project.load_script()
    if not script.segmenty:
        script = generuj(project, llm)

    ui.naglowek("Etap 1 — scenariusz")
    ui.info(
        f"{len(script.segmenty)} segmentów · {suma_znakow(script)} znaków · "
        f"~{szacowana_dlugosc(script):.0f} s (cel: {script.meta.docelowa_dlugosc_s} s)"
    )

    i = 0
    while i < len(script.segmenty):
        seg = script.segmenty[i]
        if tylko and seg.id != tylko:
            i += 1
            continue
        if seg.status == "approved" and not tylko:
            i += 1
            continue

        ui.panel_segmentu(seg.id, seg.status, seg.narracja, f"({len(seg.narracja)} znaków)")
        if seg.uwagi:
            ui.console.print("[dim]uwagi: " + " | ".join(teksty_uwag(seg.uwagi)) + "[/dim]")

        wybor = ui.wybor(
            "Decyzja",
            {"a": "akceptuj", "e": "edytuj", "r": "regeneruj z uwagą", "p": "pomiń", "q": "wyjdź"},
            "a",
        )
        if wybor == "q":
            project.save_script(script)
            return False
        if wybor == "p":
            i += 1
            continue
        if wybor == "a":
            seg.status = "approved"
            costs = project.load_costs()
            costs.zapisz_narracje(seg.id, seg.narracja)
            project.save_costs(costs)
            project.save_script(script)
            i += 1
            continue
        if wybor == "e":
            nowa = ui.edytuj(seg.narracja)
            if nowa:
                seg.narracja = " ".join(nowa.split())
                seg.status = "approved"
                costs = project.load_costs()
                costs.zapisz_narracje(seg.id, seg.narracja)
                project.save_costs(costs)
                project.save_script(script)
                ui.ok(f"{seg.id} zaktualizowany i zaakceptowany")
            i += 1
            continue
        if wybor == "r":
            uwaga = ui.zapytaj("Uwaga dla modelu")
            if not uwaga.strip():
                ui.warn("Pusta uwaga — pomijam regenerację.")
                continue
            try:
                regeneruj_segment(project, llm, script, seg, uwaga.strip())
            except LLMError as exc:
                ui.blad(str(exc))
            continue

    project.save_script(script)
    zatwierdzone = sum(1 for s in script.segmenty if s.status == "approved")
    if script.approved:
        ui.ok(f"Scenariusz zatwierdzony w całości ({zatwierdzone}/{len(script.segmenty)}).")
        return True
    ui.warn(f"Zatwierdzone {zatwierdzone}/{len(script.segmenty)} segmentów. Etap 2 wymaga kompletu.")
    return False

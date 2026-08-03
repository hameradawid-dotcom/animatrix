from __future__ import annotations

from pathlib import Path

from animatrix.llm import LLM
from animatrix.models import Uwaga
from animatrix.project import Project


def make_llm(project: Project) -> LLM:
    """LLM z księgowaniem tokenów wprost do costs.yaml projektu."""

    def on_usage(input_tokens: int, output_tokens: int) -> None:
        costs = project.load_costs()
        costs.zapisz_llm(input_tokens, output_tokens)
        project.save_costs(costs)

    return LLM(on_usage=on_usage)


def segment_id(index: int) -> str:
    return f"s{index + 1:02d}"


def dopisz_uwage(uwagi: list[Uwaga], etap: str, tekst: str) -> list[Uwaga]:
    uwagi.append(Uwaga(etap=etap, tekst=tekst))
    return uwagi


def teksty_uwag(uwagi: list[Uwaga]) -> list[str]:
    return [u.tekst for u in uwagi]


def dostepne_assety(project: Project) -> list[str]:
    if not project.assets_dir.exists():
        return []
    return sorted(
        project.rel(p)
        for p in project.assets_dir.rglob("*")
        if p.is_file() and not p.name.startswith(".")
    )


def zapisz_kod(sciezka: Path, kod: str) -> Path:
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    sciezka.write_text(kod, encoding="utf-8")
    return sciezka

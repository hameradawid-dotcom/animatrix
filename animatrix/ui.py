from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text as RichText

console = Console()

STATUS_KOLOR = {
    "draft": "yellow",
    "approved": "green",
    "pending": "dim",
    "generated": "cyan",
    "rendered": "blue",
    "failed": "red",
    "-": "dim",
}


def naglowek(tekst: str) -> None:
    console.print()
    console.rule(f"[bold]{tekst}[/bold]")


def info(tekst: str) -> None:
    console.print(f"[cyan]›[/cyan] {tekst}")


def ok(tekst: str) -> None:
    console.print(f"[green]✓[/green] {tekst}")


def warn(tekst: str) -> None:
    console.print(f"[yellow]![/yellow] {tekst}")


def blad(tekst: str) -> None:
    console.print(f"[red]✗[/red] {tekst}")


def status_chip(status: str) -> RichText:
    return RichText(status, style=STATUS_KOLOR.get(status, "white"))


def panel_segmentu(seg_id: str, status: str, tresc: str, tytul: str = "") -> None:
    console.print(
        Panel(
            tresc,
            title=f"[bold]{seg_id}[/bold] {tytul}".strip(),
            subtitle=f"status: {status}",
            border_style=STATUS_KOLOR.get(status, "white"),
            padding=(1, 2),
        )
    )


def wybor(pytanie: str, opcje: dict[str, str], domyslna: str) -> str:
    """Pyta o jedną literę. `opcje` to {litera: opis}."""
    opis = "  ".join(f"[bold]{k}[/bold]={v}" for k, v in opcje.items())
    console.print(f"[dim]{opis}[/dim]")
    return Prompt.ask(pytanie, choices=list(opcje), default=domyslna)


def zapytaj(pytanie: str, domyslna: str = "") -> str:
    return Prompt.ask(pytanie, default=domyslna) if domyslna else Prompt.ask(pytanie)


def edytuj(tekst: str, *, suffix: str = ".txt") -> str:
    """Otwiera $EDITOR na tymczasowym pliku. Bez ustawionego $EDITOR pyta w terminalu."""
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if not editor:
        warn("Brak zmiennej $EDITOR — edycja w terminalu (jedna linia).")
        return Prompt.ask("Nowa treść", default=tekst)

    with tempfile.NamedTemporaryFile("w+", suffix=suffix, delete=False, encoding="utf-8") as fh:
        fh.write(tekst)
        sciezka = Path(fh.name)
    try:
        subprocess.run([*editor.split(), str(sciezka)], check=False)
        return sciezka.read_text(encoding="utf-8").strip()
    finally:
        sciezka.unlink(missing_ok=True)


def tabela_statusu(
    wiersze: list[tuple[str, str, str, str, str]],
) -> Table:
    """wiersze: (id, skrót narracji, status scenariusza, status storyboardu, status sceny)"""
    t = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    t.add_column("segment", style="bold", no_wrap=True)
    t.add_column("narracja", overflow="ellipsis", max_width=52)
    t.add_column("scenariusz", no_wrap=True)
    t.add_column("storyboard", no_wrap=True)
    t.add_column("scena", no_wrap=True)
    for seg_id, narracja, s1, s2, s3 in wiersze:
        t.add_row(seg_id, narracja, status_chip(s1), status_chip(s2), status_chip(s3))
    return t


def skrot(tekst: str, limit: int = 60) -> str:
    tekst = " ".join(tekst.split())
    return tekst if len(tekst) <= limit else tekst[: limit - 1] + "…"


def otworz(sciezka: Path) -> None:
    """Próbuje otworzyć plik systemowym podglądem. Cicho odpuszcza na serwerze bez GUI."""
    for cmd in (["xdg-open"], ["open"]):
        try:
            subprocess.Popen(
                [*cmd, str(sciezka)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        except FileNotFoundError:
            continue
    info(f"Plik: {sciezka}")

from __future__ import annotations

import importlib.metadata
import importlib.util
import shutil
import sys
from pathlib import Path
from typing import Optional

import typer

from animatrix import __version__, ui
from animatrix.config import settings
from animatrix.models import ScriptMeta
from animatrix.project import DOMYSLNY_MOTYW, Project, ProjectError, dostepne_motywy
from animatrix.stages import scenes as stage_scenes
from animatrix.stages import script as stage_script
from animatrix.stages import storyboard as stage_storyboard

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Trzyetapowa produkcja animowanych explainerów: scenariusz → storyboard → sceny.",
)
assets_app = typer.Typer(no_args_is_help=True, help="Generatory assetów (mapy, ikony).")
app.add_typer(assets_app, name="assets")

NAZWA = typer.Argument(..., help="Nazwa projektu (katalog w projects/).")


def _otworz(nazwa: str) -> Project:
    try:
        return Project.open(nazwa)
    except ProjectError as exc:
        ui.blad(str(exc))
        raise typer.Exit(1)


def _obsluz(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except (ProjectError, RuntimeError) as exc:
        ui.blad(str(exc))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        ui.warn("Przerwane. Stan zapisany — wróć tą samą komendą.")
        raise typer.Exit(130)


# ---------------------------------------------------------------------------
@app.command()
def doctor(
    smoke: bool = typer.Option(False, "--smoke", help="Dodatkowo wyrenderuj testową klatkę z polskimi znakami."),
) -> None:
    """Sprawdza środowisko: Manim, ffmpeg, LaTeX, klucze API."""
    ui.naglowek("Diagnostyka środowiska")
    cfg = settings()
    problemy = 0

    ui.ok(f"Python {sys.version.split()[0]}")

    for modul, etykieta in (
        ("manim", "Manim CE"),
        ("manim_voiceover", "manim-voiceover"),
        ("manim_chemistry", "manim-chemistry"),
        ("anthropic", "Anthropic SDK"),
    ):
        if importlib.util.find_spec(modul) is None:
            ui.blad(f"{etykieta}: brak (pip install -r requirements.txt)")
            problemy += 1
            continue
        try:
            wersja = importlib.metadata.version(modul.replace("_", "-"))
        except importlib.metadata.PackageNotFoundError:
            wersja = "?"
        ui.ok(f"{etykieta} {wersja}")

    for binarka, wymagane in (("ffmpeg", True), ("ffprobe", False), ("latex", False), ("dvisvgm", False)):
        sciezka = shutil.which(binarka)
        if sciezka:
            ui.ok(f"{binarka}: {sciezka}")
        elif wymagane:
            ui.blad(f"{binarka}: brak — bez tego nie ma renderu ani scalania")
            problemy += 1
        else:
            ui.warn(f"{binarka}: brak — potrzebny tylko do MathTex/Tex (wzory)")

    if cfg.has_anthropic:
        ui.ok(f"ANTHROPIC_API_KEY ustawiony (model: {cfg.anthropic_model}, effort: {cfg.anthropic_effort})")
    else:
        ui.blad("ANTHROPIC_API_KEY: brak — bez tego nie wygenerujesz scenariusza")
        problemy += 1

    if cfg.tts_provider == "silent":
        ui.warn("ANIMATRIX_TTS=silent — sceny dostaną ciszę zamiast lektora (zero kosztów).")
    elif cfg.has_elevenlabs:
        ui.ok(f"ElevenLabs skonfigurowany (model: {cfg.elevenlabs_model_id})")
    else:
        ui.blad("ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID: brak — ustaw je albo ANIMATRIX_TTS=silent")
        problemy += 1

    ui.info(f"Katalog projektów: {cfg.projects_dir}")

    if smoke:
        problemy += _smoke_test()

    ui.console.print()
    if problemy:
        ui.blad(f"Problemów: {problemy}")
        raise typer.Exit(1)
    ui.ok("Środowisko gotowe.")


def _smoke_test() -> int:
    """Render testowej klatki z polskimi diakrytykami — sprawdza Pango i ścieżki."""
    from animatrix import render

    ui.naglowek("Test renderu (polskie znaki)")
    root = settings().projects_dir / "_smoke"
    proj = Project(root)
    for d in (proj.scenes_dir, proj.previews_dir, proj.voice_cache_dir):
        d.mkdir(parents=True, exist_ok=True)
    proj.install_runtime(DOMYSLNY_MOTYW, force=True)

    plik = proj.scenes_dir / "smoke.py"
    plik.write_text(
        "from theme import *\n\n\n"
        "class SmokeTest(Scene):\n"
        "    def construct(self):\n"
        '        t = tytul("Zażółć gęślą jaźń — ĄĆĘŁŃÓŚŹŻ")\n'
        '        p = podtytul("stężenie molowe · 0,25 mol/dm³")\n'
        "        grupa = VGroup(t, p).arrange(DOWN, buff=0.4)\n"
        "        self.add(grupa)\n",
        encoding="utf-8",
    )

    wynik = render.render(proj, plik, "SmokeTest", quality="l", still=True, out_name="smoke", voice=False, timeout=600)
    if wynik.ok:
        ui.ok(f"Klatka testowa: {wynik.output}")
        return 0
    ui.blad("Render testowy padł:")
    ui.console.print(f"[dim]{wynik.tail[-1500:]}[/dim]")
    return 1


# ---------------------------------------------------------------------------
@app.command()
def new(
    nazwa: str = NAZWA,
    temat: Optional[str] = typer.Option(None, "--temat"),
    dlugosc: Optional[int] = typer.Option(None, "--dlugosc", help="Docelowa długość filmu w sekundach."),
    grupa: Optional[str] = typer.Option(None, "--grupa", help="Grupa docelowa."),
    ton: Optional[str] = typer.Option(None, "--ton"),
    punkty: Optional[str] = typer.Option(None, "--punkty", help="Kluczowe punkty, rozdzielone średnikiem."),
    motyw: str = typer.Option(
        DOMYSLNY_MOTYW,
        "--motyw",
        help="Stylistyka: kh (korepetytorhamera.pl), misja (briefing), ciemny (neutralna).",
    ),
    format_wideo: str = typer.Option(
        "poziom",
        "--format",
        help="poziom = 16:9 (YouTube), pion = 9:16 (TikTok, Instagram Reels, Shorts).",
    ),
) -> None:
    """Tworzy nowy projekt i zbiera brief."""
    ui.naglowek("Nowy projekt")
    temat = temat or ui.zapytaj("Temat filmu")
    grupa = grupa or ui.zapytaj("Grupa docelowa", "uczniowie liceum przed maturą")
    dlugosc = dlugosc or int(ui.zapytaj("Docelowa długość (sekundy)", "90"))
    ton = ton or ui.zapytaj("Ton", "dynamiczny popularnonaukowy")
    surowe = punkty if punkty is not None else ui.zapytaj("Kluczowe punkty (średnik rozdziela)", "")
    lista_punktow = [p.strip() for p in surowe.split(";") if p.strip()]

    meta = ScriptMeta(
        temat=temat,
        docelowa_dlugosc_s=dlugosc,
        grupa_docelowa=grupa,
        ton=ton,
        kluczowe_punkty=lista_punktow,
        motyw=motyw,
        format_wideo=format_wideo,
    )
    try:
        proj = Project.create(nazwa, meta)
    except ProjectError as exc:
        ui.blad(str(exc))
        raise typer.Exit(1)

    ui.ok(f"Projekt: {proj.root}")
    ui.info("Następny krok: animatrix script " + proj.name)


@app.command()
def demo(
    nazwa: str = typer.Argument("demo-chemia", help="Nazwa projektu do utworzenia."),
    motyw: str = typer.Option(
        DOMYSLNY_MOTYW,
        "--motyw",
        help="Stylistyka: kh (korepetytorhamera.pl), misja (briefing), ciemny (neutralna).",
    ),
) -> None:
    """Tworzy gotowy projekt przykładowy (bez wywołań do modelu i do ElevenLabs)."""
    zrodlo = Path(__file__).resolve().parent / "demo"
    if not (zrodlo / "script.yaml").exists():
        ui.blad(f"Brak plików demo w {zrodlo}.")
        raise typer.Exit(1)

    meta = ScriptMeta(
        temat="Duży rocznik a matura z chemii (projekt demonstracyjny)", motyw=motyw
    )
    try:
        proj = Project.create(nazwa, meta)
    except ProjectError as exc:
        ui.blad(str(exc))
        raise typer.Exit(1)

    shutil.copyfile(zrodlo / "script.yaml", proj.script_path)
    shutil.copyfile(zrodlo / "storyboard.yaml", proj.storyboard_path)
    shutil.copyfile(zrodlo / "dane.py", proj.root / "dane.py")
    shutil.copyfile(zrodlo / "README.md", proj.root / "README.md")
    shutil.copytree(zrodlo / "assets", proj.assets_dir, dirs_exist_ok=True)
    shutil.copytree(zrodlo / "scenes", proj.scenes_dir, dirs_exist_ok=True)

    skrypt = proj.load_script()
    stan = stage_scenes.synchronizuj(proj, skrypt)
    for st in stan.segmenty:
        st.status = "generated"
    proj.save_scenes(stan)

    costs = proj.load_costs()
    for seg in skrypt.segmenty:
        costs.zapisz_narracje(seg.id, seg.narracja)
    proj.save_costs(costs)

    ui.ok(f"Projekt demonstracyjny: {proj.root}")
    ui.warn("Dane w demie są ilustracyjne — nie publikuj bez podmiany dane.py.")
    ui.info(f"Etapy 1 i 2 są zatwierdzone. Następny krok: animatrix scenes {proj.name}")


@app.command()
def script(
    nazwa: str = NAZWA,
    regen: bool = typer.Option(False, "--regen", help="Wygeneruj scenariusz od nowa (kasuje statusy i storyboard)."),
    segment: Optional[str] = typer.Option(None, "--segment", help="Wróć do jednego segmentu, np. s03."),
) -> None:
    """Etap 1: scenariusz + bramka akceptacji."""
    proj = _otworz(nazwa)
    if regen:
        potwierdz = ui.wybor(
            "Regeneracja skasuje zatwierdzone segmenty, storyboard i sceny. Kontynuować?",
            {"t": "tak", "n": "nie"},
            "n",
        )
        if potwierdz != "t":
            raise typer.Exit(0)
        from animatrix.models import Scenes, Storyboard
        from animatrix.stages.common import make_llm

        proj.save_storyboard(Storyboard())
        proj.save_scenes(Scenes())
        _obsluz(stage_script.generuj, proj, make_llm(proj))

    _obsluz(stage_script.bramka, proj, tylko=segment)


@app.command()
def storyboard(
    nazwa: str = NAZWA,
    segment: Optional[str] = typer.Option(None, "--segment"),
    bez_podgladow: bool = typer.Option(False, "--bez-podgladow", help="Nie renderuj klatek podglądowych."),
) -> None:
    """Etap 2: storyboard + klatki podglądowe + bramka akceptacji."""
    proj = _otworz(nazwa)
    _obsluz(stage_storyboard.bramka, proj, tylko=segment, bez_podgladow=bez_podgladow)


@app.command()
def scenes(
    nazwa: str = NAZWA,
    segment: Optional[str] = typer.Option(None, "--segment"),
    max_prob: int = typer.Option(3, "--max-prob", help="Ile razy model może próbować naprawić render."),
) -> None:
    """Etap 3: kod scen, render roboczy z pętlą samonaprawy, bramka akceptacji."""
    proj = _otworz(nazwa)
    _obsluz(stage_scenes.bramka, proj, tylko=segment, max_prob=max_prob)


@app.command("render-final")
def render_final(
    nazwa: str = NAZWA,
    czterok: bool = typer.Option(False, "--4k", help="Render w 2160p zamiast 1080p."),
    tylko_scal: bool = typer.Option(False, "--tylko-scal", help="Pomiń render, sklej istniejące pliki."),
) -> None:
    """Render finalny w wysokiej jakości i scalenie w jeden MP4."""
    proj = _otworz(nazwa)
    _obsluz(stage_scenes.render_finalny, proj, jakosc="k" if czterok else "h", tylko_scal=tylko_scal)


@app.command()
def sprawdz(
    nazwa: str = NAZWA,
    segment: Optional[str] = typer.Option(None, "--segment"),
    format_wideo: Optional[str] = typer.Option(
        None, "--format", help="Sprawdź w innym kadrze niż zapisany w projekcie."
    ),
) -> None:
    """Mierzy układ scen BEZ renderowania i zgłasza kolizje oraz wyjścia poza kadr."""
    from animatrix.sonda import zmierz_projekt
    from animatrix.uklad import bledy as tylko_bledy

    proj = _otworz(nazwa)
    fmt = format_wideo or proj.load_script().meta.format_wideo
    ui.naglowek(f"Kontrola układu — kadr {fmt}")

    with ui.console.status("mierzę sceny…"):
        wyniki = _obsluz(zmierz_projekt, proj, format=fmt)

    if segment:
        wyniki = [w for w in wyniki if w.id == segment]

    razem_bledow = 0
    for w in wyniki:
        if w.blad:
            ui.blad(f"{w.id}: sonda nie zmierzyła sceny")
            ui.console.print(f"[dim]{w.blad.splitlines()[-1][:160]}[/dim]")
            razem_bledow += 1
            continue

        twarde = tylko_bledy(w.uchybienia)
        uwagi = [u for u in w.uchybienia if u.waga != "blad"]
        razem_bledow += len(twarde)

        opis = f"{w.id}: {len(w.elementy)} obiektów, {w.takty} taktów"
        if twarde:
            ui.blad(opis)
        elif uwagi:
            ui.warn(opis)
        else:
            ui.ok(opis)
        for u in w.uchybienia:
            ui.console.print(f"    [dim]{u}[/dim]")

    ui.console.print()
    if razem_bledow:
        ui.blad(f"Błędów układu: {razem_bledow}")
        raise typer.Exit(1)
    ui.ok("Wszystkie sceny mieszczą się w kadrze i nic na siebie nie nachodzi.")


@app.command()
def status(nazwa: str = NAZWA) -> None:
    """Tabela stanu wszystkich segmentów na każdym etapie + koszty."""
    proj = _otworz(nazwa)
    skrypt = proj.load_script()
    sb = proj.load_storyboard()
    sc = proj.load_scenes()
    costs = proj.load_costs()

    ui.naglowek(f"{proj.name} — {skrypt.meta.temat}")

    wiersze = []
    for seg in skrypt.segmenty:
        item = sb.get(seg.id)
        st = sc.get(seg.id)
        wiersze.append(
            (
                seg.id,
                ui.skrot(seg.narracja, 52),
                seg.status,
                item.status if item else "-",
                st.status if st else "-",
            )
        )
    if wiersze:
        ui.console.print(ui.tabela_statusu(wiersze))
    else:
        ui.warn("Brak segmentów — uruchom `animatrix script`.")

    znaki = stage_script.suma_znakow(skrypt)
    ui.console.print()
    ui.info(
        f"Narracja: {znaki} znaków · szacowana długość ~{stage_script.szacowana_dlugosc(skrypt):.0f} s "
        f"(cel {skrypt.meta.docelowa_dlugosc_s} s)"
    )
    ui.info(
        f"ElevenLabs: {costs.elevenlabs_znaki} znaków w bieżącej wersji"
        + (f" (+{costs.elevenlabs_znaki_historycznie} w odrzuconych wersjach)" if costs.elevenlabs_znaki_historycznie else "")
    )
    ui.info(
        f"Model: {costs.llm_wywolania} wywołań · "
        f"{costs.llm_input_tokens} tok. wejścia · {costs.llm_output_tokens} tok. wyjścia"
    )

    finalny = proj.output_dir / "final.mp4"
    if finalny.exists():
        ui.ok(f"Gotowy film: {finalny}")


@app.command()
def projects() -> None:
    """Lista projektów."""
    lista = Project.list_all()
    if not lista:
        ui.warn(f"Brak projektów w {settings().projects_dir}")
        return
    for nazwa in lista:
        ui.console.print(f"  {nazwa}")


@app.command("sync-runtime")
def sync_runtime(
    nazwa: str = NAZWA,
    motyw: Optional[str] = typer.Option(None, "--motyw", help="Zmień stylistykę projektu."),
    force: bool = typer.Option(False, "--force", help="Nadpisz theme.py, voice.py i motyw.py."),
) -> None:
    """Aktualizuje theme.py / voice.py / motyw.py po aktualizacji narzędzia lub zmianie stylistyki."""
    proj = _otworz(nazwa)
    skrypt = proj.load_script()
    if motyw and motyw != skrypt.meta.motyw:
        if motyw not in dostepne_motywy():
            ui.blad(f"Nie znam motywu '{motyw}'. Dostępne: {', '.join(dostepne_motywy())}")
            raise typer.Exit(1)
        skrypt.meta.motyw = motyw
        proj.save_script(skrypt)
        force = True
    zapisane = _obsluz(proj.install_runtime, skrypt.meta.motyw, force=force)
    if zapisane:
        ui.ok("Zaktualizowano: " + ", ".join(zapisane))
    else:
        ui.info("Nic do zrobienia (użyj --force, żeby nadpisać).")


@assets_app.command("map-pl")
def assets_map_pl(
    nazwa: str = NAZWA,
    zrodlo: str = typer.Option(
        ...,
        "--zrodlo",
        help="GeoJSON/shapefile/URL z granicami województw (np. dane GUS albo Natural Earth).",
    ),
    kolumna: Optional[str] = typer.Option(None, "--kolumna", help="Kolumna z nazwą regionu."),
    wyjscie: str = typer.Option("assets/poland.svg", "--wyjscie"),
    szerokosc: int = typer.Option(1000, "--szerokosc"),
) -> None:
    """Buduje assets/poland.svg + poland.json (nazwy regionów w kolejności ścieżek)."""
    from animatrix.assets.maps import MapError, generuj_svg

    proj = _otworz(nazwa)
    cel = proj.root / wyjscie
    try:
        svg_path, meta_path = generuj_svg(zrodlo, cel, kolumna_nazwy=kolumna, szerokosc=szerokosc)
    except MapError as exc:
        ui.blad(str(exc))
        raise typer.Exit(1)
    ui.ok(f"Mapa: {svg_path}")
    ui.ok(f"Regiony: {meta_path}")


@app.command()
def version() -> None:
    """Wersja narzędzia."""
    ui.console.print(f"animatrix {__version__}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()

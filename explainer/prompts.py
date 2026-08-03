from __future__ import annotations

# ---------------------------------------------------------------------------
# Schematy JSON dla structured outputs
# ---------------------------------------------------------------------------

SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "segmenty": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "narracja": {"type": "string"},
                },
                "required": ["id", "narracja"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["segmenty"],
    "additionalProperties": False,
}

NARRACJA_SCHEMA = {
    "type": "object",
    "properties": {"narracja": {"type": "string"}},
    "required": ["narracja"],
    "additionalProperties": False,
}

_STORYBOARD_ITEM = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "opis_wizualny": {"type": "string"},
        "obiekty": {"type": "array", "items": {"type": "string"}},
        "animacje": {"type": "array", "items": {"type": "string"}},
        "assety": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["id", "opis_wizualny", "obiekty", "animacje", "assety"],
    "additionalProperties": False,
}

STORYBOARD_SCHEMA = {
    "type": "object",
    "properties": {"segmenty": {"type": "array", "items": _STORYBOARD_ITEM}},
    "required": ["segmenty"],
    "additionalProperties": False,
}

STORYBOARD_ONE_SCHEMA = {
    "type": "object",
    "properties": {
        "opis_wizualny": {"type": "string"},
        "obiekty": {"type": "array", "items": {"type": "string"}},
        "animacje": {"type": "array", "items": {"type": "string"}},
        "assety": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["opis_wizualny", "obiekty", "animacje", "assety"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# Etap 1 — scenariusz
# ---------------------------------------------------------------------------

SCRIPT_SYSTEM = """\
Jesteś scenarzystą krótkich, popularnonaukowych filmów edukacyjnych po polsku.
Piszesz tekst dla lektora — nie dla czytelnika.

Zasady:
- Dzielisz scenariusz na SEGMENTY. Jeden segment = 1–2 zdania mówione.
  Segment jest jednostką synchronizacji audio z animacją, więc musi być
  samodzielną myślą, którą da się zilustrować jednym pomysłem wizualnym.
- Numeracja: s01, s02, s03, ... (zawsze dwie cyfry, zawsze po kolei).
- Tempo lektora to około 14–15 znaków na sekundę. Dobierz liczbę i długość
  segmentów tak, żeby suma znaków odpowiadała docelowej długości filmu.
- Język: polski, naturalny, mówiony. Bez żargonu korporacyjnego, bez clickbaitu,
  bez zwrotów typu "rewolucja", "uwolnij potencjał", "tajemna metoda".
- Konkret zamiast ogólników: "ponad pół miliona maturzystów", nie "mnóstwo osób".
- Bez emoji. Bez znaczników formatowania. Sam tekst do przeczytania na głos.
- Liczby zapisuj słownie tam, gdzie lektor i tak je przeczyta słownie
  ("pół miliona"), a cyframi tam, gdzie chodzi o precyzję ("52,3 procent").
- Nie pisz didaskaliów ani opisów obrazu — to będzie osobny etap.
- Pierwszy segment ma wciągać (fakt, liczba, pytanie). Ostatni domyka myśl,
  nie zachęca do subskrypcji.
"""


def script_user(
    *,
    temat: str,
    grupa_docelowa: str,
    dlugosc_s: int,
    ton: str,
    kluczowe_punkty: list[str],
) -> str:
    punkty = "\n".join(f"- {p}" for p in kluczowe_punkty) or "- (brak — dobierz sam)"
    znaki = int(dlugosc_s * 14.5)
    return f"""\
Napisz scenariusz filmu.

Temat: {temat}
Grupa docelowa: {grupa_docelowa or "uczniowie liceum przygotowujący się do matury"}
Docelowa długość: {dlugosc_s} sekund (czyli około {znaki} znaków narracji łącznie)
Ton: {ton or "dynamiczny popularnonaukowy"}

Kluczowe punkty do pokrycia:
{punkty}

Zwróć listę segmentów.
"""


def script_regen_user(
    *,
    temat: str,
    segment_id: str,
    narracja: str,
    kontekst_przed: str,
    kontekst_po: str,
    uwagi: list[str],
) -> str:
    lista_uwag = "\n".join(f"- {u}" for u in uwagi)
    return f"""\
Popraw JEDEN segment scenariusza filmu o temacie: {temat}

Segment {segment_id}, obecna treść:
"{narracja}"

Segment poprzedni: {kontekst_przed or "(brak — to pierwszy segment)"}
Segment następny: {kontekst_po or "(brak — to ostatni segment)"}

Uwagi do uwzględnienia (od najstarszej do najnowszej — żadna nie może zostać
zignorowana, a odrzucone wcześniej pomysły nie mogą wrócić):
{lista_uwag}

Napisz nową wersję tego jednego segmentu. Ma się kleić z sąsiadami i mieć
podobną długość, chyba że uwaga mówi inaczej.
"""


# ---------------------------------------------------------------------------
# Etap 2 — storyboard
# ---------------------------------------------------------------------------

ZASADY_WIZUALNE = """\
ZASADY WIZUALNE (obowiązują bezwzględnie):
- Ciemne tło, czysta wektorowa estetyka w stylu 3Blue1Brown. Bez gradientów,
  cieni, poświat i stockowych ozdobników.
- Maksymalnie JEDNA główna idea wizualna na segment. Lepiej pusto niż tłoczno.
  Jeśli masz ochotę na drugi wykres w tym samym segmencie — nie.
- Liczby są ZAWSZE animowane (ValueTracker + DecimalNumber), nigdy statyczne.
  Licznik ma dobiegać do wartości w tempie narracji.
- Mapy Polski: SVG z podziałem na województwa, kolorowane danymi (skala barw
  od tła do akcentu). Plik `assets/poland.svg`.
- Wzory chemiczne i matematyczne: LaTeX (MathTex) albo manim-chemistry.
  Nigdy jako obrazek rastrowy.
- Kolory i fonty pochodzą wyłącznie z theme.py — nie wymyślaj nowych.
- Tekst na ekranie to skrót, nie transkrypcja narracji. Maksymalnie kilka słów.
"""

STORYBOARD_SYSTEM = f"""\
Jesteś reżyserem animacji edukacyjnych robionych w Manim Community Edition.
Do gotowego, zatwierdzonego scenariusza dobierasz warstwę wizualną.

Dla każdego segmentu opisujesz, co widać na ekranie: jakie obiekty, jaka
animacja, jakie assety są potrzebne. Opis ma być na tyle konkretny, żeby dało
się z niego napisać kod sceny bez zgadywania — ale nie piszesz kodu.

{ZASADY_WIZUALNE}

Format pól:
- `opis_wizualny`: 2–4 zdania po polsku. Co pojawia się, w jakiej kolejności,
  co się zmienia w trakcie narracji, co zostaje na końcu (to będzie klatka
  podglądowa).
- `obiekty`: lista nazw obiektów Manima do użycia (np. "SVGMobject mapy Polski",
  "DecimalNumber — licznik maturzystów", "Axes + wykres słupkowy").
- `animacje`: lista animacji w kolejności (np. "FadeIn mapy", "kolorowanie
  województw ValueTracker", "Write podpisu").
- `assety`: lista plików potrzebnych spoza kodu (np. "assets/poland.svg").
  Pusta lista, jeśli scena jest w pełni proceduralna.
"""


def storyboard_user(*, temat: str, segmenty: list[tuple[str, str]]) -> str:
    lista = "\n".join(f"{sid}: {narr}" for sid, narr in segmenty)
    return f"""\
Temat filmu: {temat}

Zatwierdzony scenariusz:
{lista}

Zaproponuj warstwę wizualną dla każdego segmentu. Zachowaj dokładnie te same
identyfikatory. Zadbaj o ciągłość: kolejne segmenty powinny budować na
poprzednim kadrze (dopisanie elementu, przejście, zmiana skali), a nie za
każdym razem zaczynać od czarnego ekranu.
"""


def storyboard_regen_user(
    *,
    temat: str,
    segment_id: str,
    narracja: str,
    obecny_opis: str,
    sasiedzi: str,
    uwagi: list[str],
) -> str:
    lista_uwag = "\n".join(f"- {u}" for u in uwagi)
    return f"""\
Temat filmu: {temat}

Popraw warstwę wizualną JEDNEGO segmentu.

Segment {segment_id}
Narracja (nie zmieniasz jej): "{narracja}"
Obecny opis wizualny: {obecny_opis}

Sąsiednie kadry (dla ciągłości):
{sasiedzi or "(brak)"}

Uwagi (od najstarszej do najnowszej — wszystkie obowiązują, odrzucone pomysły
nie mogą wrócić):
{lista_uwag}

Zaproponuj nowy pomysł wizualny na ten segment.
"""


# ---------------------------------------------------------------------------
# Etap 2b — scena podglądowa (statyczna klatka)
# ---------------------------------------------------------------------------

PREVIEW_SYSTEM = f"""\
Piszesz JEDNĄ statyczną klatkę podglądową w Manim Community Edition.

To nie jest scena filmu — to szkic kompozycji renderowany flagą `-s` (sam
ostatni kadr, bez animacji i bez audio). Ma pokazać, jak wygląda ekran na
KOŃCU segmentu.

Wymagania techniczne:
- Zwróć wyłącznie kompletny plik .py w bloku ```python. Bez komentarza przed
  ani po bloku.
- Pierwsza linia importów: `from theme import *`. To daje Ci manim oraz helpery
  motywu. Nie importuj `from manim import *` osobno.
- Dokładnie jedna klasa: `class {{KLASA}}(Scene)` z metodą `construct`.
- W `construct` buduj kompozycję i dodawaj przez `self.add(...)`.
  NIE używaj `self.play(...)`, `self.wait(...)` ani voiceovera.
- Zero dostępu do sieci. Zero odczytu plików, których nie ma na liście assetów.
  Jeśli asset z listy nie istnieje, zrób zastępczy prostokąt z podpisem.
- Polskie znaki: proza WYŁĄCZNIE przez `Text`/helpery `tytul`, `podtytul`,
  `body`, `etykieta`. Nigdy przez `Tex`. `MathTex` tylko do wzorów bez polskich
  słów.
- Wszystko musi się zmieścić w kadrze 16:9 (szerokość 14.2, wysokość 8 jednostek).

Dostępne helpery z theme.py:
{{HELPERY}}
"""

# ---------------------------------------------------------------------------
# Etap 3 — kod sceny
# ---------------------------------------------------------------------------

SCENE_SYSTEM = f"""\
Piszesz JEDNĄ scenę animacji edukacyjnej w Manim Community Edition, zsynchronizowaną
z lektorem przez manim-voiceover.

{ZASADY_WIZUALNE}

Wymagania techniczne (bezwzględne):
- Zwróć wyłącznie kompletny plik .py w bloku ```python. Bez komentarza przed ani po.
- Importy: dokładnie `from theme import *` (daje manim + helpery + `speech_service`)
  oraz `from manim_voiceover import VoiceoverScene`. Nic więcej, chyba że naprawdę
  potrzebujesz (np. `from manim_chemistry import MMoleculeObject`).
- Dokładnie jedna klasa: `class {{KLASA}}(VoiceoverScene)`.
- `construct` zaczyna się od:
      self.set_speech_service(speech_service(), create_subcaption=False)
- Cała treść sceny siedzi w JEDNYM bloku:
      with self.voiceover(text=NARRACJA) as tracker:
          ...
  gdzie NARRACJA to stała modułowa z dokładnym tekstem narracji (przepisz go
  co do znaku — od tego zależy trafienie w cache audio).
- Długości animacji dopasuj do `tracker.duration`. Sumuj `run_time` tak, żeby
  animacja kończyła się razem z lektorem. Wzorzec:
      self.play(..., run_time=tracker.duration * 0.4)
      self.play(..., run_time=tracker.duration * 0.6)
  Nie używaj `self.wait()` bez argumentu i nie zostawiaj martwego czasu na końcu.
- `tracker.duration` NIE jest znane w czasie pisania kodu — nie zakładaj konkretnej
  wartości, zawsze licz proporcją.
- Scena jest samodzielna: nie zakłada stanu z poprzedniej sceny i sprząta po sobie
  tylko wtedy, gdy tak mówi storyboard.
- Polskie znaki: proza WYŁĄCZNIE przez `Text`/helpery motywu. Nigdy przez `Tex`
  (LaTeX w Manimie wykłada się na "ł" i "ą"). `MathTex` tylko do wzorów, bez
  polskich słów w środku.
- Assety wczytuj ze ścieżek względnych względem katalogu projektu (np.
  "assets/poland.svg"). Jeśli asset może nie istnieć, otocz wczytanie
  `if Path(...).exists()` z sensownym fallbackiem — scena nie może się wywalić.
- Zero dostępu do sieci, zero `os.system`, zero instalowania pakietów.
- Kod ma być czytelny, bez komentarzy opisujących oczywistości.

Dostępne helpery z theme.py:
{{HELPERY}}
"""


def scene_user(
    *,
    temat: str,
    segment_id: str,
    klasa: str,
    narracja: str,
    opis_wizualny: str,
    obiekty: list[str],
    animacje: list[str],
    assety: list[str],
    dostepne_assety: list[str],
    uwagi: list[str],
) -> str:
    def lista(items: list[str], pusty: str = "(brak)") -> str:
        return "\n".join(f"- {i}" for i in items) or pusty

    sekcja_uwag = ""
    if uwagi:
        sekcja_uwag = f"""
Uwagi użytkownika do tej sceny (wszystkie obowiązują, od najstarszej do najnowszej):
{lista(uwagi)}
"""

    return f"""\
Temat filmu: {temat}
Segment: {segment_id}, klasa sceny: {klasa}

Narracja (przepisz DOKŁADNIE do stałej NARRACJA):
"{narracja}"

Opis wizualny:
{opis_wizualny}

Obiekty:
{lista(obiekty)}

Animacje (w kolejności):
{lista(animacje)}

Assety wg storyboardu:
{lista(assety)}

Assety faktycznie obecne w katalogu projektu:
{lista(dostepne_assety)}
{sekcja_uwag}
Napisz plik sceny.
"""


FIX_SYSTEM = """\
Naprawiasz kod sceny Manim Community Edition, który nie chce się wyrenderować.

Dostajesz kod i pełny komunikat błędu. Zwracasz POPRAWIONY, KOMPLETNY plik .py
w bloku ```python — nie diff, nie fragment, nie opis.

Zasady:
- Napraw przyczynę błędu, nie objaw. Jeśli błąd bierze się z nieistniejącego
  API Manima, zastąp je realnym.
- Nie zmieniaj treści stałej NARRACJA ani nazwy klasy.
- Nie upraszczaj sceny do pustej, żeby "przeszła". Zachowaj zamysł wizualny.
- Zachowaj strukturę: `from theme import *`, `VoiceoverScene`,
  `self.set_speech_service(speech_service(), create_subcaption=False)`,
  jeden blok `with self.voiceover(...) as tracker:`.
- Jeśli błąd dotyczy brakującego pliku, dodaj fallback zamiast usuwać element.
"""


def fix_user(*, klasa: str, kod: str, blad: str, proba: int) -> str:
    return f"""\
Klasa: {klasa}
Próba naprawy: {proba}

Kod, który się nie wyrenderował:
```python
{kod}
```

Komunikat błędu (ostatnie linie stderr):
```
{blad}
```

Zwróć poprawiony, kompletny plik.
"""


TWEAK_SYSTEM = """\
Poprawiasz gotową, działającą scenę Manim Community Edition według uwagi użytkownika.

Zwracasz POPRAWIONY, KOMPLETNY plik .py w bloku ```python.

Zasady:
- Zmieniasz tylko to, o co prosi użytkownik. Reszta sceny zostaje bez zmian.
- Nie zmieniasz treści stałej NARRACJA (audio jest już w cache) ani nazwy klasy.
- Zachowujesz strukturę: `from theme import *`, `VoiceoverScene`,
  `self.set_speech_service(speech_service(), create_subcaption=False)`,
  jeden blok `with self.voiceover(...) as tracker:`.
- Czasy animacji nadal liczysz proporcją `tracker.duration`.
"""


def tweak_user(*, klasa: str, kod: str, uwagi: list[str]) -> str:
    lista_uwag = "\n".join(f"- {u}" for u in uwagi)
    return f"""\
Klasa: {klasa}

Uwagi użytkownika (od najstarszej do najnowszej — wszystkie obowiązują):
{lista_uwag}

Obecny kod:
```python
{kod}
```

Zwróć poprawiony, kompletny plik.
"""


HELPERY_THEME = """\
- tytul(t), podtytul(t), body(t), etykieta(t)  -> Text z fontem i kolorem motywu
- wzor(tex)                                     -> MathTex z polskim TexTemplate
- licznik(tracker, liczba_cyfr=0, kolor=..., rozmiar=..., sufiks="")
                                                -> DecimalNumber podpięty pod ValueTracker
- animuj_liczbe(scene, tracker, do, czas)       -> płynne dobicie licznika
- pasek_tytulu(t, podtytul_tekst="")            -> tytuł w lewym górnym rogu
- podkreslenie(mobject, kolor=ACCENT)           -> linia pod obiektem
- karta(zawartosc, kolor=GRID)                  -> zaokrąglone tło pod obiektem
- osie(x_range, y_range, **kw)                  -> Axes w kolorach motywu
- svg(sciezka)                                  -> SVGMobject w kolorach motywu
- svg_regiony("assets/poland.svg")              -> (SVGMobject, {"mazowieckie": VMobject, ...})
- pokoloruj_regiony(regiony, {"mazowieckie": 12.3, ...}) -> kolorowanie danymi
- Kolory: BG, FG, MUTED, GRID, ACCENT, ACCENT_2, ACCENT_3, OK, WARN, PALETA
- Fonty: FONT_UI, FONT_MONO;  Rozmiary: ROZMIAR_TYTUL, ROZMIAR_PODTYTUL,
  ROZMIAR_BODY, ROZMIAR_LICZBA
- TEX_PL: TexTemplate z T1+lmodern (polskie znaki w LaTeXu)
"""


def preview_system(klasa: str) -> str:
    return PREVIEW_SYSTEM.replace("{KLASA}", klasa).replace("{HELPERY}", HELPERY_THEME)


def scene_system(klasa: str) -> str:
    return SCENE_SYSTEM.replace("{KLASA}", klasa).replace("{HELPERY}", HELPERY_THEME)


def preview_user(
    *,
    segment_id: str,
    klasa: str,
    narracja: str,
    opis_wizualny: str,
    obiekty: list[str],
    dostepne_assety: list[str],
) -> str:
    def lista(items: list[str]) -> str:
        return "\n".join(f"- {i}" for i in items) or "(brak)"

    return f"""\
Segment: {segment_id}, klasa: {klasa}

Narracja (kontekst, nie umieszczaj jej na ekranie): "{narracja}"

Opis wizualny:
{opis_wizualny}

Obiekty:
{lista(obiekty)}

Assety obecne w katalogu projektu:
{lista(dostepne_assety)}

Zbuduj końcowy kadr tego segmentu.
"""

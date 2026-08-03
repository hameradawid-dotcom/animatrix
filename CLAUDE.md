# animatrix

Lokalne narzędzie do produkcji animowanych explainerów po polsku (Manim + ElevenLabs).
Docelowo TikTok i Reels — format pionowy jest domyślnym przypadkiem, nie wyjątkiem.

Pełna dokumentacja użytkownika: `README.md`.

---

## Jak to działa dziś

Scena to **spec** (`sceny/sNN.yaml`): nazwa szablonu + parametry. Interfejs pokazuje je
jako formularz, silnik zamienia w obiekty Manima, walidator sprawdza kompozycję **przed**
renderem. Sceny na surowym Pythonie zostają dostępne przez `szablon: kod`.

```
wklejony scenariusz  →  podzial.py tnie na segmenty (deterministycznie, bez modelu)
                     →  spec na segment: szablon + parametry
                     →  sonda mierzy układ BEZ renderu (~2 s)
                     →  render roboczy -ql z lektorem
                     →  render finalny -qh + scalenie ffmpeg
```

## Mapa kodu

| Plik | Za co odpowiada |
|---|---|
| `scena.py` | model `SceneSpec`, nazwy ról kolorów, odwołania `@NAZWA` do `dane.py` |
| `szablony/baza.py` | sloty (`nad`/`rdzen`/`pod`/`stopka`), `zloz()` — składacz kadru, `Beat` |
| `szablony/{liczby,wykresy,siatki,karty}.py` | 9 szablonów; każdy ma `Parametry` (pydantic) i `przyklad` |
| `szablony/odtwarzacz.py` | spec → kompozycja → takty; wołany z `runtime/scena_ze_specu.py` |
| `formaty.py` | 9:16 / 4:5 / 1:1 / 16:9, strefy bezpieczne, progi czytelności |
| `uklad.py` | `Kadr`, `Prostokat`, `waliduj()` — bez importu Manima, testowalne samodzielnie |
| `sonda.py` + `_sonda_runner.py` | pomiar układu w osobnym procesie, bez renderowania |
| `podzial.py` | podział wklejonego scenariusza na zdania i segmenty |
| `uslugi.py` | bezstanowe operacje — wspólne dla CLI i API |
| `zadania.py` | rejestr zadań w tle: postęp, anulowanie, SSE |
| `serwer.py` + `web/index.html` | interfejs (FastAPI + vanilla JS, bez node) |
| `runtime/theme.py` | helpery wizualne kopiowane do projektu; **własność użytkownika** |
| `runtime/motyw_*.py` | palety: `kh` (korepetytorhamera.pl), `misja`, `ciemny` |

## Zasady

- **Polski w UI i w nazwach kodu.** Ten projekt łamie zwykłą konwencję „angielski w kodzie" —
  identyfikatory są po polsku, konsekwentnie. Nie mieszaj.
- **Komentarz tylko wtedy, gdy tłumaczy *dlaczego*.** Nie opisujemy, co robi kod.
- **Odstępy wyłącznie ze skali** `sp(4|8|12|16|24|32|48|64|96|128)`. `sp()` rzuca na wartość
  spoza skali — to celowe, nie do „naprawienia".
- **Szablon nie ustawia pozycji.** Buduje treść i wkłada w slot; kadrem zarządza `zloz()`.
  Współrzędna absolutna w szablonie to błąd projektowy.
- **Kolory nazwą roli** (`akcent`, `alarm`, `wyroznienie`, `stonowany`), nigdy hexem —
  inaczej zmiana motywu wymaga dotykania scen.
- Nowy szablon musi mieć `przyklad`, który przechodzi walidację układu we wszystkich
  formatach (pilnuje tego `tests/test_szablony_uklad.py`).

## Pułapki, które już raz kosztowały film

Każda z tych rzeczy przeszła do gotowego materiału, zanim ją wykryto. Nie cofaj ich.

1. **`DecimalNumber.set_value` odbudowuje glify w pierwotnym `font_size`** i gubi każde
   przeskalowanie nałożone później. `licznik()` w `theme.py` zapamiętuje wysokość przy
   pierwszej klatce i ją przywraca. Bez tego licznik puchnie na pół kadru.
2. **Sufiks licznika idzie do LaTeXa.** Surowy `%` to początek komentarza — znika,
   zostawiając pusty obiekt rozdymający bounding box. Stąd `_sufiks_tex()`.
3. **Manim nie przelicza `frame_width` po `-r`.** `theme.py` wymusza kadr z proporcji
   pikseli, a `PX_NA_JEDNOSTKE` liczy z wysokości FORMATU (nie z `config.pixel_height`),
   żeby render roboczy i finalny miały ten sam layout. Heurystyka „pion = 1920 px"
   kłamała o 4:5 (1350 px).
4. **Cele animacji liczone przy budowie sceny są nieaktualne**, bo `zloz()` przesuwa
   i skaluje grupę później. Licz je na żywo w takcie (patrz `y_progu` w `siatki.py`).
5. **`Create` na grupie z tekstem obrysowuje litery** zamiast je pisać — `wejscie()`
   sprawdza rekurencyjnie i używa `Write`.
6. **Manim gubi atrybuty `id` z SVG** — nazwy regionów mapy idą z sidecar-owego JSON-a
   o tej samej nazwie, po kolejności ścieżek.
7. **LaTeX jest wymagany**, nie opcjonalny: liczniki składają cyfry `MathTex`-em.

## Walidacja układu

Dwa poziomy, celowo:

- `theme.sprawdz_uklad(elementy)` — w scenie, na nazwanych elementach. `ANIMATRIX_STRICT=1`
  zamienia uchybienia w twardy błąd renderu.
- `animatrix sprawdz <projekt> [--format 4:5]` — sonda mierzy wszystkie sceny bez renderu.
  Rozwija zwykłe `VGroup` na dzieci, bo kolizje **wewnątrz** grupy chowają się
  w prostokącie opisanym na całej grupie.

Progi: kolizja > 12% pola mniejszego elementu, element poniżej 5% sąsiada to marker
(kropka na łamanej, grot strzałki), zawieranie to relacja, nie kolizja.

## Testy

```bash
pytest -q                    # wszystko
pytest -q -m "not slow"      # bez renderowania (sekundy)
```

`tests/test_szablony_uklad.py` to główny test regresji kompozycji: każdy szablon
w każdym formacie, mierzony sondą.

## Czego jeszcze nie ma

- `animatrix sprawdz` **raportuje, ale nie blokuje** renderu.
- Brak presetów eksportu (waga pliku, parametry pod upload).
- Dobór szablonu do segmentu jest ręczny — model tego nie proponuje.
- **Strefy bezpieczne w `formaty.py` to przybliżenia** (sierpień 2026), niezweryfikowane
  na prawdziwym telefonie. Zmieniają się z każdą aktualizacją TikToka.
- Ścieżki ElevenLabs i Anthropic nigdy nie były odpalone na prawdziwych kluczach.

# animatrix

Lokalne narzędzie CLI do produkcji animowanych explainerów edukacyjnych po polsku.
Prowadzi przez trzy etapy z bramkami akceptacji: **scenariusz → storyboard → sceny**.
Nic nie renderuje się w wysokiej jakości, zanim nie zaakceptujesz wersji roboczej.

Animacje robi Manim Community Edition — programistycznie, deterministycznie.
Żadnego generatywnego wideo.

---

## Jak to działa

```
brief  →  ETAP 1: scenariusz     →  bramka: akceptuj / edytuj / regeneruj z uwagą
          (segmenty po 1–2 zdania)

       →  ETAP 2: storyboard     →  bramka: oceniasz na klatce PNG, nie na opisie
          (+ statyczne klatki podglądowe)

       →  ETAP 3: sceny          →  bramka: oglądasz render roboczy -ql z audio
          (kod Manima + pętla samonaprawy)

       →  render finalny 1080p/4K + scalenie ffmpeg → output/final.mp4
```

Segment jest jednostką wszystkiego: jedno zdanie narracji, jeden pomysł wizualny,
jedna klasa sceny, jeden plik MP4. Poprawka jednej sceny **nigdy** nie wymusza
rerenderu pozostałych.

---

## Instalacja

Wymagane w systemie: **Python 3.11+**, **ffmpeg**, opcjonalnie **LaTeX**
(`latex` + `dvisvgm`) jeśli chcesz wzorów przez `MathTex`.

```bash
# Ubuntu / Debian
sudo apt install ffmpeg libpango1.0-dev
sudo apt install texlive-latex-extra texlive-science dvisvgm   # opcjonalnie, do wzorów

# macOS
brew install ffmpeg pango
brew install --cask mactex-no-gui                              # opcjonalnie
```

```bash
git clone <repo> && cd animatrix
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

cp .env.example .env    # uzupełnij klucze
animatrix doctor --smoke
```

`doctor --smoke` renderuje testową klatkę z polskimi diakrytykami — jeśli
przejdzie, środowisko jest gotowe.

---

## Szybki start bez kluczy API

```bash
animatrix demo moj-test          # gotowy projekt: mapa Polski, licznik, wykres, cząsteczka
animatrix scenes moj-test        # render roboczy + bramka akceptacji
animatrix render-final moj-test  # 1080p + scalenie
```

Demo nie wysyła ani jednego zapytania do Anthropic i ani jednego znaku do
ElevenLabs (ustaw `ANIMATRIX_TTS=silent`). **Liczby w demie są ilustracyjne.**

---

## Prawdziwy projekt

```bash
animatrix new duzy-rocznik
animatrix script duzy-rocznik        # etap 1 + bramka
animatrix storyboard duzy-rocznik    # etap 2 + klatki podglądowe + bramka
animatrix scenes duzy-rocznik        # etap 3 + samonaprawa + bramka
animatrix render-final duzy-rocznik  # 1080p (--4k dla 2160p)
animatrix status duzy-rocznik        # tabela stanu + koszty
```

Możesz zamknąć narzędzie w dowolnym momencie — cały stan siedzi w plikach YAML
i wczytuje się przy następnym uruchomieniu.

### Bramki akceptacji

Na każdym etapie, dla każdego segmentu:

| klawisz | co robi |
|---|---|
| `a` | akceptuj |
| `e` | edytuj ręcznie (otwiera `$EDITOR`) |
| `r` | regeneruj z uwagą słowną |
| `o` | otwórz podgląd / render |
| `p` | pomiń (zostaw `draft`, wróć później) |
| `q` | wyjdź, zapisując stan |

Uwagi zapisują się per segment w YAML-u i **wracają do modelu przy każdej
kolejnej regeneracji** — żeby nie proponował raz po raz tego samego, co już
odrzuciłeś.

Wracasz do jednego segmentu flagą `--segment`:

```bash
animatrix scenes duzy-rocznik --segment s03
```

---

## Struktura projektu

```
projects/duzy-rocznik/
├── script.yaml        # segmenty narracji + statusy + historia uwag
├── storyboard.yaml    # opisy wizualne 1:1 z segmentami
├── scenes.yaml        # stan kodu scen, licznik prób naprawy, ścieżki renderów
├── costs.yaml         # znaki wysłane do ElevenLabs, tokeny modelu
├── theme.py           # paleta, fonty, helpery — TWOJA własność, edytuj śmiało
├── voice.py           # wybór silnika mowy (ElevenLabs / cisza)
├── dane.py            # (opcjonalnie) liczby do wykresów, oddzielone od kodu scen
├── assets/            # poland.svg, .mol, zdjęcia
├── scenes/s01.py …    # jedna klasa VoiceoverScene na segment
├── previews/          # statyczne klatki PNG z etapu 2
├── renders/draft/     # rendery robocze -ql
├── renders/final/     # rendery finalne -qh
├── .cache/voiceover/  # cache audio — klucz to hash tekstu, więc edycja
└── output/final.mp4   #   jednej sceny nie regeneruje audio pozostałych
```

---

## Zasady wizualne

Wbudowane w prompt generatora storyboardu i kodu scen:

- ciemne tło, czysta wektorowa estetyka w stylu 3Blue1Brown
- maksymalnie **jedna** główna idea wizualna na segment
- liczby zawsze animowane (`ValueTracker` + `DecimalNumber`), nigdy statyczne
- mapy Polski jako SVG z podziałem na województwa, kolorowane danymi
- wzory przez `MathTex` albo manim-chemistry — nigdy jako obrazek
- paleta i fonty wyłącznie z `theme.py`

### Polskie znaki

To jest realna pułapka i narzędzie rozwiązuje ją tak:

- **proza zawsze przez `Text`** (Pango) — helpery `tytul`, `podtytul`, `body`,
  `etykieta`. Diakrytyki działają bez konfiguracji.
- **`Tex` nigdy do polskich słów** — domyślny `TexTemplate` Manima wykłada się
  na „ł" i „ą".
- do wzorów jest `wzor()` z `TEX_PL` (`T1` + `lmodern`), który polskie znaki
  obsługuje poprawnie, gdyby były potrzebne w LaTeX-u.

Zasada jest wpisana w prompt systemowy generatora scen, więc model jej pilnuje.

---

## Koszty

`animatrix status` pokazuje licznik znaków wysłanych do ElevenLabs — osobno
dla bieżącej wersji scenariusza i osobno dla wersji odrzuconych.

Trzy rzeczy trzymają rachunek nisko:

1. **Cache audio per projekt** — kluczem jest hash tekstu i konfiguracji głosu.
   Rerender sceny po poprawce wizualnej nie kosztuje ani jednego znaku, bo
   narracja się nie zmieniła (prompt zabrania modelowi ruszać stałej `NARRACJA`).
2. **Klatki podglądowe z etapu 2 renderują się bez audio.**
3. **`ANIMATRIX_TTS=silent`** — cisza o długości oszacowanej z tempa mowy.
   `tracker.duration` działa normalnie, więc timing animacji jest realistyczny,
   a rachunek zerowy. Dobre do dopracowywania warstwy wizualnej.

---

## Mapy z danymi

```bash
animatrix assets map-pl moj-projekt \
  --zrodlo wojewodztwa.geojson \
  --kolumna nazwa
```

Powstaje `assets/poland.svg` **oraz** `assets/poland.json` z nazwami regionów
w kolejności ścieżek. Sidecar jest konieczny, bo Manim gubi atrybuty `id` przy
imporcie SVG — bez niego nie da się trafić w konkretne województwo. W scenie:

```python
mapa, regiony = svg_regiony("assets/poland.svg")
pokoloruj_regiony(regiony, {"mazowieckie": 14.0, "slaskie": 11.5})
```

---

## Pętla samonaprawy

Po wygenerowaniu kodu sceny narzędzie od razu renderuje ją w `-ql`. Jeśli render
padnie, przechwytuje stderr, wysyła kod + błąd do modelu i ponawia — domyślnie
do 3 razy (`--max-prob`). Po wyczerpaniu prób pokazuje błąd i pyta, co dalej:
edytować kod ręcznie, podpowiedzieć modelowi, czy pominąć segment.

Model dostaje instrukcję, żeby naprawiać przyczynę, a nie upraszczać sceny do
pustej, byle „przeszła".

---

## Konfiguracja

Wszystko w `.env` (patrz `.env.example`):

| zmienna | domyślnie | do czego |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | generator scenariusza, storyboardu i kodu |
| `ANTHROPIC_MODEL` | `claude-opus-5` | tańsza alternatywa: `claude-sonnet-5` |
| `ANTHROPIC_EFFORT` | `high` | `low` … `max` |
| `ELEVENLABS_API_KEY` | — | lektor |
| `ELEVENLABS_VOICE_ID` | — | ID głosu z panelu ElevenLabs |
| `ELEVENLABS_MODEL_ID` | `eleven_multilingual_v2` | polski czyta poprawnie |
| `ANIMATRIX_TTS` | `elevenlabs` | `silent` = zero kosztów |
| `ANIMATRIX_PROJECTS_DIR` | `projects` | gdzie trzymać projekty |

---

## Testy

```bash
pytest -m "not slow"   # szybkie, bez renderu
pytest                 # + pełny przepływ z podstawionym modelem i prawdziwym renderem
```

Testy oznaczone `slow` przechodzą cały pipeline z atrapą modelu: pierwsza wersja
kodu sceny jest celowo zepsuta, więc sprawdzają też pętlę samonaprawy i scalanie
ffmpeg-iem. Nie dzwonią do żadnego API.

---

## Czego narzędzie nie robi

- nie używa generatywnego wideo (Sora, Runway itp.) — tylko Manim
- nie renderuje w wysokiej jakości przed akceptacją wersji roboczej
- nie łączy wielu segmentów w jedną klasę sceny

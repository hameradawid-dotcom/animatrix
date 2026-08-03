"""Motyw korepetytorhamera.pl — paleta Warm Science.

Jasne, ciepłe tło zamiast czerni. To świadome odejście od domyślnej estetyki
3Blue1Brown na rzecz spójności z marką: film ma wyglądać jak przedłużenie
strony, a nie jak osobny produkt.

Reguły marki, których pilnują sceny:
- tła sekcji tylko BG albo BG_ALT; czysta biel wyłącznie jako tło karty
- brak gradientów, cieni, blura i poświat
- nagłówki sentence case, bez wersalików poza krótkimi tagami
- brak emoji
"""

NAZWA = "kh"
STYL = "kh"

# --- paleta Warm Science ---
BG = "#FFFBF5"           # główne tło sekcji
BG_ALT = "#F5EFDF"       # kremowy akcent tła
POWIERZCHNIA = "#FFFFFF"  # tło karty — biel TYLKO tutaj
SIATKA = "#E4DAC6"       # linie osi, obrysy

FG = "#1A0F33"           # tekst główny
FG_2 = "#4A3870"         # tekst drugorzędny
MUTED = "#7A6B96"        # podpisy, etykiety osi

ACCENT = "#5B21B6"       # akcent marki (Dawid)
ACCENT_2 = "#FB7185"     # koral (Sonia)
ACCENT_3 = "#F59E0B"     # warm — wyróżnienie liczby
OK = "#10B981"
WARN = "#DC2626"

PALETA = [ACCENT, ACCENT_2, ACCENT_3, OK, MUTED]

# --- typografia ---
FONT_HEAD = "Space Grotesk"
FONT_UI = "Inter"
FONT_MONO = "DejaVu Sans Mono"

WAGA_TYTUL = "BOLD"
WAGA_PODTYTUL = "MEDIUM"
WAGA_BODY = "NORMAL"

# ujemny tracking nagłówków (em) — z BRAND.md: -0.02 do -0.03
# tracking nagłówków w jednostkach Pango (1024 = 1 pt); BRAND.md mówi -0.02..-0.03em
TRACKING_TYTUL = -300

ROZMIAR_TYTUL = 44
ROZMIAR_PODTYTUL = 28
ROZMIAR_BODY = 26
ROZMIAR_ETYKIETA = 20
ROZMIAR_LICZBA = 84

# --- skala odstępów (px z BRAND.md → jednostki Manima przy kadrze 8 jednostek
# wysokości = 1080 px). Nigdy nie wpisuj wartości spoza tej skali.
SKALA_PX = [4, 8, 12, 16, 24, 32, 48, 64, 96, 128]
PX_NA_JEDNOSTKE = 1080 / 8

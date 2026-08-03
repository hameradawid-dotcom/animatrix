# Projekt demonstracyjny — „Duży rocznik a matura z chemii"

To gotowy projekt do sprawdzenia, czy render działa na Twojej maszynie, **bez
jednego zapytania do Anthropic i bez jednego znaku wysłanego do ElevenLabs**.

> ⚠️ **Wszystkie liczby w tym projekcie są ilustracyjne.** Nie pochodzą z CKE
> ani GUS. Nie publikuj tego jako materiału edukacyjnego bez podmiany danych
> w `dane.py` na źródłowe.

Pokrywa cztery typy wizualizacji z założeń narzędzia:

| segment | co pokazuje |
|---|---|
| s01 | tytuł, podkreślenie, chip |
| s02 | animowany licznik (ValueTracker + DecimalNumber) |
| s03 | mapa Polski z SVG, województwa kolorowane danymi |
| s04 | wykres słupkowy zdawalności |
| s05 | cząsteczka z manim-chemistry + wzór w LaTeX-u |

## Pochodzenie assetów

`assets/poland.svg` wygenerowano komendą `animatrix assets map-pl` z warstwy
granic województw z repozytorium [ppatrzyk/polska-geojson]
(https://github.com/ppatrzyk/polska-geojson) (`wojewodztwa-medium.geojson`,
uproszczenie 1500 m). Sprawdź licencję źródła, zanim użyjesz mapy komercyjnie.

`assets/etanol.mol` to ręcznie napisany plik MOL V2000 (etanol, 3 atomy ciężkie).

## Jak uruchomić

```bash
animatrix demo moj-test          # tworzy projekt z gotowym scenariuszem i scenami
animatrix scenes moj-test        # render roboczy + bramka akceptacji
animatrix render-final moj-test  # 1080p + scalenie w output/final.mp4
```

Etapy 1 i 2 są już zatwierdzone — demo zaczyna się od etapu 3, żeby nie wymagać
klucza do modelu. Sceny nadal przechodzą przez bramkę akceptacji, tak jak
w normalnym projekcie.

Bez klucza ElevenLabs ustaw `ANIMATRIX_TTS=silent` w `.env` — sceny dostaną
ciszę o długości oszacowanej z tempa mowy, więc timing animacji będzie
realistyczny.

"""Dane dla przykładowego projektu.

⚠️ WSZYSTKIE LICZBY SĄ ILUSTRACYJNE. Nie pochodzą z CKE ani GUS i nie nadają się
do publikacji. Zanim zrobisz z tego prawdziwy film — podmień je na źródłowe.

Trzymanie danych w osobnym module, a nie w kodzie scen, to celowy wzorzec:
podmieniasz liczby w jednym miejscu i rerenderujesz tylko te sceny, których
dotyczy zmiana.
"""

MATURZYSCI_TYS = 300.0

# udział województwa w roczniku, w procentach (suma ≈ 100)
UDZIAL_WOJEWODZTW = {
    "mazowieckie": 14.0,
    "slaskie": 11.5,
    "wielkopolskie": 9.5,
    "malopolskie": 8.9,
    "dolnoslaskie": 7.3,
    "pomorskie": 6.1,
    "lodzkie": 6.2,
    "podkarpackie": 5.4,
    "lubelskie": 5.3,
    "kujawsko-pomorskie": 5.2,
    "zachodniopomorskie": 4.3,
    "warminsko-mazurskie": 3.6,
    "swietokrzyskie": 3.1,
    "podlaskie": 3.0,
    "lubuskie": 2.5,
    "opolskie": 2.1,
}

UDZIAL_CHEMII_PROC = 8.3

# (rok, zdawalność w procentach)
ZDAWALNOSC = [
    (2022, 58),
    (2023, 56),
    (2024, 55),
    (2025, 52),
    (2026, 49),
]

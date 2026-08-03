"""Dane do filmu „Dostać się na lekarski w 2027".

KAŻDA liczba tutaj ma źródło. Nic nie jest zmyślone. Wartości oznaczone
SZACUNEK to ekstrapolacje — w filmie muszą być podpisane jako szacunek.

Źródła:
[1] korepetytorhamera.pl/blog/podwojny-rocznik-2027-jak-powstal
[2] korepetytorhamera.pl/blog/matura-2027-rekordowy-rocznik
[3] korepetytorhamera.pl/blog/progi-na-medycyne-2026-czy-wzrosna
[4] korepetytorhamera.pl/rekrutacja-2026/pum-szczecin/lekarski
[5] rekrutacja.pum.edu.pl/wazne-informacje/progi-punktowe (oficjalne progi PUM)
[6] CKE — arkusz maturalny chemia rozszerzona (60 pkt)
[7] forsal.pl / bankier.pl — liczba maturzystów 2026: 321 314
"""

# --- liczebność roczników maturalnych (tys. osób) --------------------------
# 2025 i 2026 to dane, 2027 i 2028 to prognozy demograficzne. [1][2][7]
ROCZNIKI = [
    (2025, 256, "dane"),
    (2026, 321, "dane"),
    (2027, 386, "prognoza"),
    (2028, 271, "prognoza"),
]
WZROST_2026_2027_PROC = 20.2  # 386/321 - 1

# --- PUM Szczecin, kierunek lekarski --------------------------------------
PUM_MIEJSC = 255  # [4]
PUM_KANDYDATOW = 5202  # [4]
PUM_NA_MIEJSCE = 20.4  # [4]

# Progi końcowe wg oficjalnej tabeli PUM — rok = rok rekrutacji. [5]
# Uwaga: próg NIE rośnie monotonicznie. W 2024 spadł. To istotne, bo psuje
# wygodną narrację „progi zawsze rosną" — i dlatego zostaje w filmie.
PUM_PROGI = [
    (2023, 158, "dane"),
    (2024, 143, "dane"),
    (2025, 149, "dane"),
]
# Rekrutacja 2026, kolejne listy rankingowe. [4]
PUM_LISTY_2026 = [(1, 175), (2, 166), (3, 163)]
PUM_PROG_2026_SZAC = 159  # szacowany próg końcowy ±12 [4]

# SZACUNEK: 2025→2026 próg urósł o 10 pkt przy wzroście rocznika o 25%.
# Rocznik 2027 rośnie o 20% względem 2026, więc zakładamy podobną dynamikę.
# To ekstrapolacja, nie dane — w kadrze musi być podpisana.
PUM_CEL_2027_SZAC = 170

# --- przelicznik rekrutacyjny PUM ------------------------------------------
# „Dwa dowolne z {biologia, chemia, fizyka, matematyka}, rozsz. 1% = 1 pkt.
#  2 × 100 = 200" [4]
PUM_MAX_PKT = 200
PUM_PRZEDMIOTY = 2

# --- matura z chemii --------------------------------------------------------
ARKUSZ_CHEMIA_PKT = 60  # [6]
PKT_ARKUSZA_NA_PKT_REKRUTACJI = 100 / ARKUSZ_CHEMIA_PKT  # 1 pkt arkusza = 1,67 pkt

SREDNIA_CHEMIA = [(2025, 43), (2026, 41)]  # % [3]

# --- wyliczenia pochodne (arytmetyka z powyższych) --------------------------
SKOK_PROGU_PKT = PUM_PROG_2026_SZAC - PUM_PROGI[-1][1]  # 159 - 149 = 10
SKOK_PROGU_W_ZADANIACH = round(SKOK_PROGU_PKT / PKT_ARKUSZA_NA_PKT_REKRUTACJI)  # 6

TOP_PROC_2026 = PUM_MIEJSC / PUM_KANDYDATOW * 100  # 4,90%
KANDYDACI_2027_SZAC = round(PUM_KANDYDATOW * (1 + WZROST_2026_2027_PROC / 100))
TOP_PROC_2027 = PUM_MIEJSC / KANDYDACI_2027_SZAC * 100  # 4,08%

CEL_PROC_2027 = round(PUM_CEL_2027_SZAC / PUM_MAX_PKT * 100)  # 85%

# --- miejsca na lekarskim w Polsce -----------------------------------------
MIEJSCA_PL = [(2025, 10504), (2026, 10705)]  # 2026/27 to projekt rozporządzenia [3]
WZROST_MIEJSC_PROC = 1.9

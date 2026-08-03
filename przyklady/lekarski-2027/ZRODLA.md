# Źródła danych — „Dostać się na lekarski w 2027"

Każda liczba w `dane.py` pochodzi z jednego z poniższych źródeł. Nic nie jest
zmyślone. Wartości oznaczone SZACUNEK to ekstrapolacje i w kadrze są podpisane.

## Liczebność roczników maturalnych

| rok | liczba | źródło |
|---|---|---|
| 2025 | ~256 tys. | korepetytorhamera.pl/blog/matura-2027-rekordowy-rocznik |
| 2026 | 321 314 | bankier.pl, forsal.pl (dane CKE o sesji majowej 2026) |
| 2027 | ~386 tys. | korepetytorhamera.pl/blog/podwojny-rocznik-2027-jak-powstal |
| 2028 | ~271 tys. | jw. |

**Rozbieżność do wyjaśnienia:** blog `progi-na-medycyne-2026-czy-wzrosna` podaje
dla 2026 ok. 345 tys., podczas gdy dwa pozostałe teksty i źródła zewnętrzne
mówią o 320–321 tys. W filmie użyto 321 tys.

## PUM Szczecin, kierunek lekarski

| dana | wartość | źródło |
|---|---|---|
| miejsca | 255 | korepetytorhamera.pl/rekrutacja-2026/pum-szczecin/lekarski |
| kandydaci | 5202 | jw. |
| na miejsce | 20,4 | jw. |
| próg 2023/24 | 158 | rekrutacja.pum.edu.pl/wazne-informacje/progi-punktowe |
| próg 2024/25 | 143 | jw. |
| próg 2025/26 | 149 | jw. (zgodne z blogiem) |
| listy 2026 | 175 / 166 / 163 | korepetytorhamera.pl/rekrutacja-2026/... |
| szac. próg końcowy 2026 | ~159 (±12) | jw. |
| przelicznik | 2 rozszerzenia z {bio, chem, fiz, mat}, 1% = 1 pkt, max 200 | jw. |

**Rozbieżność do wyjaśnienia:** blog `progi-na-medycyne-2026` podaje dla PUM
16 666 kandydatów, strona rekrutacyjna — 5202. Prawdopodobnie pierwsza liczba
to zgłoszenia na wszystkie kierunki PUM, druga na sam lekarski. W filmie użyto
5202, bo dotyczy wprost kierunku lekarskiego.

## Matura z chemii

| dana | wartość | źródło |
|---|---|---|
| punktów na arkuszu rozszerzonym | 60 | arkusze CKE (m.in. MCHP-R0-100-A-2605) |
| średni wynik 2025 | 43% | korepetytorhamera.pl/blog/progi-na-medycyne-2026-czy-wzrosna |
| średni wynik 2026 | 41% | jw. |

## Miejsca na lekarskim w Polsce

| rok akad. | limit | źródło |
|---|---|---|
| 2025/26 | 10 504 | korepetytorhamera.pl/blog/progi-na-medycyne-2026-czy-wzrosna |
| 2026/27 | 10 705 (projekt) | jw. |

## Co jest wyliczeniem, a nie danymi

Arytmetyka wprost z powyższych liczb — pokazana w filmie jako wniosek, nie fakt
źródłowy:

- wzrost rocznika 2026→2027: 386 / 321 − 1 = **+20,2%**
- wzrost limitu miejsc: 10 705 / 10 504 − 1 = **+1,9%**
- skok progu PUM 2025→2026: 159 − 149 = **10 pkt**
- 1 pkt arkusza chemii = 100/60 = **1,67 pkt rekrutacyjnego**
- skok progu w zadaniach: 10 / 1,67 = **6 punktów na arkuszu**
- odsetek przyjętych 2026: 255 / 5202 = **4,90%**
- odsetek przyjętych 2027 przy tej samej liczbie miejsc: 255 / 6253 = **4,08%**

## Co jest SZACUNKIEM

`PUM_CEL_2027_SZAC = 170` — ekstrapolacja. Próg wzrósł o 10 pkt przy wzroście
rocznika o 25% (2025→2026); rocznik 2027 rośnie o 20% względem 2026, więc
przyjęto podobną dynamikę: 159 + ~11 ≈ 170.

To nie jest prognoza uczelni ani żadnego organu. W scenie s12 jest to podpisane
w kadrze („SZACUNEK NA PODSTAWIE DYNAMIKI 2025→2026") i w narracji słowem
„około". Przed publikacją warto to zweryfikować, gdy PUM opublikuje próg
końcowy rekrutacji 2026.

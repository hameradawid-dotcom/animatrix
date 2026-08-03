"""Rejestr zadań w tle: render z postępem, który da się anulować.

CLI renderuje synchronicznie i to mu wystarcza. Interfejs nie może zablokować
żądania HTTP na dwie minuty, a użytkownik musi mieć jak przerwać render, który
puścił przez pomyłkę. Stąd wątek, kolejka zdarzeń i flaga anulowania.

Bez zewnętrznego brokera — narzędzie jest lokalne, a zadania giną razem
z procesem serwera. To celowe: kolejka przeżywająca restart wymagałaby stanu,
którego nie ma czym odtworzyć.
"""

from __future__ import annotations

import queue
import threading
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

Stan = str  # "czeka" | "trwa" | "gotowe" | "blad" | "anulowane"


@dataclass
class Zdarzenie:
    rodzaj: str  # "postep" | "log" | "koniec"
    dane: dict[str, Any] = field(default_factory=dict)


@dataclass
class Zadanie:
    id: str
    opis: str
    projekt: str
    stan: Stan = "czeka"
    postep: float | None = None
    komunikat: str = ""
    wynik: Any = None
    blad: str | None = None
    _anuluj: threading.Event = field(default_factory=threading.Event, repr=False)
    _sluchacze: list[queue.Queue] = field(default_factory=list, repr=False)
    _zamek: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def anulowane(self) -> bool:
        return self._anuluj.is_set()

    @property
    def skonczone(self) -> bool:
        return self.stan in ("gotowe", "blad", "anulowane")

    def anuluj(self) -> None:
        self._anuluj.set()

    def _rozeslij(self, zdarzenie: Zdarzenie) -> None:
        with self._zamek:
            sluchacze = list(self._sluchacze)
        for kolejka in sluchacze:
            kolejka.put(zdarzenie)

    def zakoncz(self, stan: Stan, *, wynik: Any = None, blad: str | None = None) -> None:
        """Przejście w stan końcowy MUSI być atomowe.

        `subskrybuj` sprawdza `skonczone` pod tym samym zamkiem — bez tego
        odbiorca potrafił zobaczyć stan „blad" zanim zapisał się jego powód
        i dostawał zdarzenie końcowe z pustym komunikatem.
        """
        with self._zamek:
            self.wynik = wynik
            self.blad = blad
            if stan == "gotowe":
                self.postep = 1.0
            self.stan = stan
            sluchacze = list(self._sluchacze)
        podsumowanie = self.podsumowanie()
        for kolejka in sluchacze:
            kolejka.put(Zdarzenie("koniec", podsumowanie))

    def raportuj(self, *, postep: float | None = None, komunikat: str = "") -> None:
        if postep is not None:
            self.postep = postep
        if komunikat:
            self.komunikat = komunikat
        self._rozeslij(Zdarzenie("postep", {"postep": self.postep, "komunikat": self.komunikat}))

    def subskrybuj(self) -> Iterator[Zdarzenie]:
        """Strumień zdarzeń dla jednego odbiorcy (SSE w interfejsie).

        Zadanie już skończone zwraca od razu zdarzenie końcowe — inaczej klient,
        który podłączył się o sekundę za późno, wisiałby w nieskończoność.
        """
        kolejka: queue.Queue = queue.Queue()
        with self._zamek:
            if self.skonczone:
                kolejka.put(Zdarzenie("koniec", self.podsumowanie()))
            else:
                self._sluchacze.append(kolejka)
        try:
            while True:
                zdarzenie = kolejka.get()
                yield zdarzenie
                if zdarzenie.rodzaj == "koniec":
                    return
        finally:
            with self._zamek:
                if kolejka in self._sluchacze:
                    self._sluchacze.remove(kolejka)

    def podsumowanie(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "opis": self.opis,
            "projekt": self.projekt,
            "stan": self.stan,
            "postep": self.postep,
            "komunikat": self.komunikat,
            "blad": self.blad,
            "wynik": self.wynik,
        }


class Rejestr:
    def __init__(self, maks_historii: int = 50):
        self._zadania: dict[str, Zadanie] = {}
        self._kolejnosc: list[str] = []
        self._zamek = threading.Lock()
        self.maks_historii = maks_historii

    def uruchom(
        self,
        opis: str,
        projekt: str,
        praca: Callable[[Zadanie], Any],
    ) -> Zadanie:
        zadanie = Zadanie(id=uuid.uuid4().hex[:12], opis=opis, projekt=projekt)
        with self._zamek:
            self._zadania[zadanie.id] = zadanie
            self._kolejnosc.append(zadanie.id)
            self._posprzataj()

        def _bieg() -> None:
            zadanie.stan = "trwa"
            zadanie.raportuj(postep=0.0, komunikat="start")
            try:
                wynik = praca(zadanie)
            except Exception as exc:
                zadanie.zakoncz("blad", blad=f"{exc}\n{traceback.format_exc(limit=4)}")
                return
            zadanie.zakoncz("anulowane" if zadanie.anulowane else "gotowe", wynik=wynik)

        threading.Thread(target=_bieg, name=f"animatrix-{zadanie.id}", daemon=True).start()
        return zadanie

    def _posprzataj(self) -> None:
        while len(self._kolejnosc) > self.maks_historii:
            stare = self._kolejnosc.pop(0)
            zadanie = self._zadania.get(stare)
            if zadanie is not None and not zadanie.skonczone:
                self._kolejnosc.append(stare)
                return
            self._zadania.pop(stare, None)

    def pobierz(self, zadanie_id: str) -> Zadanie | None:
        return self._zadania.get(zadanie_id)

    def lista(self, projekt: str | None = None) -> list[Zadanie]:
        with self._zamek:
            zadania = [self._zadania[i] for i in self._kolejnosc if i in self._zadania]
        if projekt:
            zadania = [z for z in zadania if z.projekt == projekt]
        return zadania

    def aktywne(self, projekt: str) -> Zadanie | None:
        return next((z for z in self.lista(projekt) if not z.skonczone), None)


REJESTR = Rejestr()

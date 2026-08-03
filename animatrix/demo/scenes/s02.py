from dane import MATURZYSCI_TYS
from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = "Weźmy rocznik, w którym do matury podchodzi trzysta tysięcy osób."


class Scena_S02(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)

        pasek = pasek_misji(2, "Skala")
        tracker_wartosci = ValueTracker(0)
        liczba = licznik(tracker_wartosci, liczba_cyfr=0, sufiks=" tys.")
        podpis = podtytul("maturzystów w roczniku")
        podpis.next_to(liczba, DOWN, buff=sp(32))

        with self.voiceover(text=NARRACJA) as tracker:
            self.play(wejscie(pasek), run_time=tracker.duration * 0.15)
            self.add(liczba)
            self.play(wejscie(podpis), run_time=tracker.duration * 0.15)
            self.play(
                tracker_wartosci.animate.set_value(MATURZYSCI_TYS),
                run_time=tracker.duration * 0.7,
                rate_func=rate_functions.ease_out_cubic,
            )

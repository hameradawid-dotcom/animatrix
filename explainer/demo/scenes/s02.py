from dane import MATURZYSCI_TYS
from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = "Weźmy rocznik, w którym do matury podchodzi trzysta tysięcy osób."


class Scena_S02(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)

        tracker_wartosci = ValueTracker(0)
        liczba = licznik(tracker_wartosci, liczba_cyfr=0, sufiks=" tys.")
        podpis = podtytul("maturzystów w roczniku")
        podpis.next_to(liczba, DOWN, buff=0.5)

        with self.voiceover(text=NARRACJA) as tracker:
            self.add(liczba)
            self.play(FadeIn(podpis, shift=UP * 0.2), run_time=tracker.duration * 0.2)
            self.play(
                tracker_wartosci.animate.set_value(MATURZYSCI_TYS),
                run_time=tracker.duration * 0.8,
                rate_func=rate_functions.ease_out_cubic,
            )

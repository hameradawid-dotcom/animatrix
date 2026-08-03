from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = "Ten materiał to przykład działania narzędzia — wszystkie liczby są ilustracyjne."


class Scena_S01(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)

        naglowek = tytul("Duży rocznik a matura z chemii")
        linia = podkreslenie(naglowek)
        chip = karta(etykieta("dane przykładowe"))
        chip.next_to(naglowek, DOWN, buff=0.7)

        with self.voiceover(text=NARRACJA) as tracker:
            self.play(Write(naglowek), run_time=tracker.duration * 0.45)
            self.play(Create(linia), run_time=tracker.duration * 0.2)
            self.play(FadeIn(chip, shift=UP * 0.3), run_time=tracker.duration * 0.35)

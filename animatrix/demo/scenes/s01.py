from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = "Ten materiał to przykład działania narzędzia — wszystkie liczby są ilustracyjne."


class Scena_S01(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)

        pasek = pasek_misji(1, "Wprowadzenie")
        naglowek = tytul("Duży rocznik a matura z chemii")
        kreska = podkreslenie(naglowek)
        chip = karta(etykieta("dane przykładowe"), padding=24)
        chip.next_to(naglowek, DOWN, buff=sp(64))

        with self.voiceover(text=NARRACJA) as tracker:
            self.play(wejscie(pasek), run_time=tracker.duration * 0.2)
            self.play(Write(naglowek), run_time=tracker.duration * 0.4)
            self.play(Create(kreska), run_time=tracker.duration * 0.15)
            self.play(wejscie(chip), run_time=tracker.duration * 0.25)

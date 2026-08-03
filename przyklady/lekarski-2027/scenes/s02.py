from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = "Za rok będzie trudniej i da się to policzyć co do punktu."


class Scena_S02(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)

        etykieta_misji = mono("// ZADANIE", color=ACCENT)
        naglowek = tytul("Lekarski\n2027", font_size=skaluj(56))
        naglowek.set_color(FG)
        podpis = podtytul("PUM Szczecin")

        blok = VGroup(etykieta_misji, naglowek, podpis).arrange(DOWN, buff=sp(24))
        ramka = naroza(blok, margines=48)

        with self.voiceover(text=NARRACJA) as tracker:
            self.play(Write(etykieta_misji), run_time=tracker.duration * 0.2)
            self.play(Write(naglowek), run_time=tracker.duration * 0.4)
            self.play(
                Create(ramka),
                FadeIn(podpis),
                run_time=tracker.duration * 0.4,
            )

from dane import SREDNIA_CHEMIA
from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = (
    "A teraz rzecz, która wygląda na błąd. "
    "Średni wynik z chemii spadł z czterdziestu trzech procent na czterdzieści jeden."
)

SKALA = 0.055


class Scena_S07(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)

        pasek = pasek_misji(5, "Średnia z chemii")

        podstawa = Line(LEFT * 1.5, RIGHT * 1.5, color=SIATKA, stroke_width=2).shift(DOWN * 1.8)

        slupki, opisy = VGroup(), VGroup()
        for i, (rok, proc) in enumerate(SREDNIA_CHEMIA):
            kolor = MUTED if i == 0 else WARN
            s = Rectangle(width=0.85, height=proc * SKALA, fill_color=kolor, fill_opacity=1.0, stroke_width=0)
            s.align_to(podstawa, DOWN).set_x(-0.7 + i * 1.4)
            slupki.add(s)
            opisy.add(
                VGroup(
                    body(f"{proc}%", color=kolor, font_size=skaluj(30)),
                    mono(str(rok)),
                )
                .arrange(DOWN, buff=sp(8))
                .next_to(s, UP, buff=sp(12))
            )

        strzalka = Arrow(
            slupki[0].get_top() + RIGHT * 0.45 + UP * 0.15,
            slupki[1].get_top() + LEFT * 0.1 + UP * 0.15,
            color=WARN,
            stroke_width=5,
            max_tip_length_to_length_ratio=0.2,
            buff=0.1,
        )
        spadek = body("−2 pkt proc.", color=WARN, font_size=skaluj(22))
        spadek.next_to(podstawa, DOWN, buff=sp(48))

        with self.voiceover(text=NARRACJA) as tracker:
            self.play(wejscie(pasek), Create(podstawa), run_time=tracker.duration * 0.18)
            self.play(GrowFromEdge(slupki[0], DOWN), FadeIn(opisy[0]), run_time=tracker.duration * 0.27)
            self.play(GrowFromEdge(slupki[1], DOWN), FadeIn(opisy[1]), run_time=tracker.duration * 0.27)
            self.play(GrowArrow(strzalka), FadeIn(spadek), run_time=tracker.duration * 0.28)

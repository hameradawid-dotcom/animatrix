from dane import UDZIAL_CHEMII_PROC, ZDAWALNOSC
from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = (
    "Chemię rozszerzoną wybiera co dwunasty z nich, "
    "a kiedy rocznik rośnie, średni wynik zwykle lekko spada."
)

SZEROKOSC_SLUPKA = 0.9
ODSTEP = 0.45
SKALA_Y = 0.075


class Scena_S04(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)

        chip = karta(etykieta(f"chemia rozszerzona: {UDZIAL_CHEMII_PROC}% rocznika"))
        chip.to_edge(UP, buff=0.6)

        podstawa = Line(LEFT * 5.5, RIGHT * 5.5, color=MUTED, stroke_width=2)
        podstawa.shift(DOWN * 2.6)

        slupki = VGroup()
        etykiety = VGroup()
        wartosci = VGroup()
        szerokosc_calkowita = len(ZDAWALNOSC) * SZEROKOSC_SLUPKA + (len(ZDAWALNOSC) - 1) * ODSTEP
        start_x = -szerokosc_calkowita / 2 + SZEROKOSC_SLUPKA / 2

        for i, (rok, procent) in enumerate(ZDAWALNOSC):
            wysokosc = procent * SKALA_Y
            kolor = WARN if i == len(ZDAWALNOSC) - 1 else ACCENT
            slupek = Rectangle(
                width=SZEROKOSC_SLUPKA,
                height=wysokosc,
                fill_color=kolor,
                fill_opacity=1.0,
                stroke_width=0,
            )
            slupek.move_to(podstawa.get_left() + RIGHT * 0)
            slupek.align_to(podstawa, DOWN)
            slupek.set_x(start_x + i * (SZEROKOSC_SLUPKA + ODSTEP))
            slupki.add(slupek)

            rok_txt = etykieta(str(rok))
            rok_txt.next_to(slupek, DOWN, buff=0.22)
            etykiety.add(rok_txt)

            proc_txt = body(f"{procent}%", font_size=22, color=kolor)
            proc_txt.next_to(slupek, UP, buff=0.18)
            wartosci.add(proc_txt)

        with self.voiceover(text=NARRACJA) as tracker:
            self.play(
                FadeIn(chip, shift=DOWN * 0.2),
                Create(podstawa),
                run_time=tracker.duration * 0.2,
            )
            self.play(
                LaggedStart(
                    *[GrowFromEdge(s, DOWN) for s in slupki],
                    lag_ratio=0.25,
                ),
                run_time=tracker.duration * 0.45,
            )
            self.play(
                FadeIn(etykiety),
                FadeIn(wartosci),
                run_time=tracker.duration * 0.2,
            )
            self.play(
                Indicate(slupki[-1], color=WARN, scale_factor=1.06),
                run_time=tracker.duration * 0.15,
            )

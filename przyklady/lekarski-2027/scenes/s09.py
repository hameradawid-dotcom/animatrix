from dane import TOP_PROC_2026, TOP_PROC_2027
from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = (
    "W tej rekrutacji trzeba było być w najlepszych pięciu procentach kandydatów. "
    "Za rok w czterech."
)

BOK = 10


class Scena_S09(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)

        pasek = pasek_misji(7, "Ile miejsc w stawce")

        siatka = VGroup(
            *[
                Square(side_length=0.26, stroke_width=1.2, stroke_color=SIATKA, fill_opacity=0)
                for _ in range(BOK * BOK)
            ]
        )
        siatka.arrange_in_grid(rows=BOK, cols=BOK, buff=sp(12))
        siatka.move_to(UP * 0.2)

        podpis = body("100 kandydatów", font_size=skaluj(24)).next_to(siatka, UP, buff=sp(32))

        t_wynik = ValueTracker(TOP_PROC_2026)
        wynik = licznik(t_wynik, liczba_cyfr=1, rozmiar=skaluj(56), kolor=ACCENT, sufiks="%")
        opis = mono("TRZEBA BYĆ W TOP")
        blok = VGroup(opis, wynik).arrange(DOWN, buff=sp(12))
        blok.next_to(siatka, DOWN, buff=sp(48))

        with self.voiceover(text=NARRACJA) as tracker:
            self.play(wejscie(pasek), FadeIn(podpis), run_time=tracker.duration * 0.15)
            self.play(
                LaggedStart(*[FadeIn(s) for s in siatka], lag_ratio=0.006),
                run_time=tracker.duration * 0.25,
            )
            self.add(wynik)
            self.play(FadeIn(opis), run_time=tracker.duration * 0.08)
            self.play(
                *[
                    siatka[i].animate.set_fill(ACCENT, opacity=1.0).set_stroke(ACCENT)
                    for i in range(5)
                ],
                run_time=tracker.duration * 0.22,
            )
            self.play(
                siatka[4].animate.set_fill(WARN, opacity=1.0).set_stroke(WARN),
                t_wynik.animate.set_value(TOP_PROC_2027),
                run_time=tracker.duration * 0.2,
            )
            self.play(
                Indicate(siatka[4], color=WARN, scale_factor=1.6),
                run_time=tracker.duration * 0.1,
            )

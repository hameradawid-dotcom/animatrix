from dane import WZROST_2026_2027_PROC, WZROST_MIEJSC_PROC
from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = "Miejsc na lekarskim w całej Polsce przybywa o dwa procent. Kandydatów o dwadzieścia."

DLUGOSC_MAX = 3.2


class Scena_S04(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)

        pasek = pasek_misji(2, "Nożyce")

        def blok(opis: str, proc: float, kolor: str, y: float):
            podpis = body(opis, font_size=skaluj(24), color=FG)
            wartosc = body(f"+{proc:.0f}%", color=kolor, font_size=skaluj(34))
            naglowek = VGroup(podpis, wartosc).arrange(RIGHT, buff=sp(24))
            naglowek.set_y(y + 0.42)

            lewo = LEFT * (DLUGOSC_MAX / 2)
            tor = Line(lewo, lewo + RIGHT * DLUGOSC_MAX, color=SIATKA, stroke_width=2).set_y(y)
            wypelnienie = Line(
                tor.get_start(),
                tor.get_start() + RIGHT * DLUGOSC_MAX * (proc / WZROST_2026_2027_PROC),
                color=kolor,
                stroke_width=16,
            )
            return naglowek, tor, wypelnienie

        m_nag, m_tor, m_fill = blok("miejsca", WZROST_MIEJSC_PROC, MUTED, 1.1)
        k_nag, k_tor, k_fill = blok("kandydaci", WZROST_2026_2027_PROC, WARN, -0.7)

        puenta = body("dziesięć razy\nszybciej", color=ACCENT_3, font_size=skaluj(28))
        puenta.next_to(k_tor, DOWN, buff=sp(96))

        with self.voiceover(text=NARRACJA) as tracker:
            self.play(wejscie(pasek), run_time=tracker.duration * 0.12)
            self.play(
                FadeIn(m_nag), Create(m_tor), FadeIn(k_nag), Create(k_tor),
                run_time=tracker.duration * 0.18,
            )
            self.play(
                Create(m_fill),
                run_time=tracker.duration * 0.22,
                rate_func=rate_functions.ease_out_cubic,
            )
            self.play(
                Create(k_fill),
                run_time=tracker.duration * 0.32,
                rate_func=rate_functions.ease_out_cubic,
            )
            self.play(FadeIn(puenta, shift=UP * sp(12)), run_time=tracker.duration * 0.16)

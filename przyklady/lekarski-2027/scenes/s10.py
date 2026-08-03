from dane import ARKUSZ_CHEMIA_PKT, PKT_ARKUSZA_NA_PKT_REKRUTACJI
from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = (
    "Arkusz z chemii ma sześćdziesiąt punktów. "
    "Jeden punkt na arkuszu to prawie dwa punkty w rekrutacji."
)

KOLUMNY = 10


class Scena_S10(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)

        pasek = pasek_misji(8, "Arkusz z chemii")

        kratki = VGroup(
            *[
                Square(side_length=0.32, stroke_width=1.2, stroke_color=SIATKA, fill_opacity=0)
                for _ in range(ARKUSZ_CHEMIA_PKT)
            ]
        )
        kratki.arrange_in_grid(rows=ARKUSZ_CHEMIA_PKT // KOLUMNY, cols=KOLUMNY, buff=sp(12))
        kratki.move_to(UP * 0.5)

        podpis = etykieta(f"{ARKUSZ_CHEMIA_PKT} punktów na arkuszu")
        podpis.next_to(kratki, UP, buff=sp(32))

        rownanie = VGroup(
            body("1 pkt na arkuszu", font_size=skaluj(24)),
            body("=", color=MUTED, font_size=skaluj(22)),
            body(f"{PKT_ARKUSZA_NA_PKT_REKRUTACJI:.2f} pkt\nw rekrutacji", color=ACCENT_3, font_size=skaluj(24)),
        ).arrange(DOWN, buff=sp(12))
        rownanie.next_to(kratki, DOWN, buff=sp(48))

        with self.voiceover(text=NARRACJA) as tracker:
            self.play(wejscie(pasek), FadeIn(podpis), run_time=tracker.duration * 0.14)
            self.play(
                LaggedStart(*[FadeIn(k) for k in kratki], lag_ratio=0.012),
                run_time=tracker.duration * 0.36,
            )
            self.play(
                kratki[0].animate.set_fill(ACCENT, opacity=1.0).set_stroke(ACCENT),
                run_time=tracker.duration * 0.14,
            )
            self.play(
                LaggedStart(*[FadeIn(w, shift=UP * sp(8)) for w in rownanie], lag_ratio=0.3),
                run_time=tracker.duration * 0.26,
            )
            self.play(Indicate(rownanie[2], color=ACCENT_3, scale_factor=1.1), run_time=tracker.duration * 0.1)

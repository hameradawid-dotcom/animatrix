from dane import ARKUSZ_CHEMIA_PKT, SKOK_PROGU_PKT, SKOK_PROGU_W_ZADANIACH
from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = (
    "Skok progu o dziesięć punktów to sześć zadań na arkuszu. "
    "Tyle dzieli cię od rocznika przed tobą."
)

KOLUMNY = 10


class Scena_S11(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)

        pasek = pasek_misji(9, "Cena jednego roku")

        kratki = VGroup(
            *[
                Square(side_length=0.32, stroke_width=1.2, stroke_color=SIATKA, fill_opacity=0)
                for _ in range(ARKUSZ_CHEMIA_PKT)
            ]
        )
        kratki.arrange_in_grid(rows=ARKUSZ_CHEMIA_PKT // KOLUMNY, cols=KOLUMNY, buff=sp(12))
        kratki.move_to(UP * 0.5)

        t_skok = ValueTracker(0)
        skok = licznik(t_skok, rozmiar=skaluj(52), kolor=WARN, sufiks=" pkt progu", docelowa=SKOK_PROGU_PKT)
        strzalka_gora = mono("PRÓG 149 → 159", color=MUTED)
        blok_skok = VGroup(strzalka_gora, skok).arrange(DOWN, buff=sp(12))
        blok_skok.next_to(kratki, UP, buff=sp(32))

        puenta = body(f"{SKOK_PROGU_W_ZADANIACH} zadania\nna arkuszu", color=WARN, font_size=skaluj(30))
        puenta.next_to(kratki, DOWN, buff=sp(48))

        with self.voiceover(text=NARRACJA) as tracker:
            self.play(wejscie(pasek), FadeIn(strzalka_gora), run_time=tracker.duration * 0.14)
            self.add(skok)
            self.play(
                LaggedStart(*[FadeIn(k) for k in kratki], lag_ratio=0.008),
                t_skok.animate.set_value(SKOK_PROGU_PKT),
                run_time=tracker.duration * 0.3,
            )
            self.play(
                LaggedStart(
                    *[
                        kratki[i].animate.set_fill(WARN, opacity=1.0).set_stroke(WARN)
                        for i in range(SKOK_PROGU_W_ZADANIACH)
                    ],
                    lag_ratio=0.35,
                ),
                run_time=tracker.duration * 0.36,
            )
            self.play(FadeIn(puenta, shift=UP * sp(12)), run_time=tracker.duration * 0.2)

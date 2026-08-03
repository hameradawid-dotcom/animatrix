from dane import UDZIAL_WOJEWODZTW
from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = "Rozkładają się nierówno: najwięcej maturzystów mieszka na Mazowszu, Śląsku i w Wielkopolsce."

PODPISY = {
    "mazowieckie": "Mazowsze",
    "slaskie": "Śląsk",
    "wielkopolskie": "Wielkopolska",
}


class Scena_S03(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)

        mapa, regiony = svg_regiony("assets/poland.svg")
        mapa.scale_to_fit_height(5.8).to_edge(LEFT, buff=1.4)

        maks = max(UDZIAL_WOJEWODZTW.values())
        docelowe = {
            nazwa: interpolate_color(
                ManimColor(GRID), ManimColor(ACCENT), UDZIAL_WOJEWODZTW.get(nazwa, 0) / maks
            )
            for nazwa in regiony
        }

        # Legenda po prawej — podpisy na mapie nachodziłyby na siebie przy
        # sąsiadujących województwach.
        legenda = VGroup()
        for nazwa, tekst in PODPISY.items():
            probka = Square(side_length=0.28, fill_color=docelowe[nazwa], fill_opacity=1.0, stroke_width=0)
            opis = body(f"{tekst} — {UDZIAL_WOJEWODZTW[nazwa]}%", font_size=24)
            legenda.add(VGroup(probka, opis).arrange(RIGHT, buff=0.3, aligned_edge=LEFT))
        legenda.arrange(DOWN, buff=0.45, aligned_edge=LEFT).to_edge(RIGHT, buff=1.2)

        with self.voiceover(text=NARRACJA) as tracker:
            self.play(FadeIn(mapa), run_time=tracker.duration * 0.25)
            self.play(
                *[
                    sub.animate.set_fill(docelowe[nazwa], opacity=1.0)
                    for nazwa, sub in regiony.items()
                ],
                run_time=tracker.duration * 0.4,
            )
            self.play(
                LaggedStart(*[FadeIn(w, shift=RIGHT * 0.2) for w in legenda], lag_ratio=0.3),
                run_time=tracker.duration * 0.35,
            )

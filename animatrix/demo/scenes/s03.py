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

        pasek = pasek_misji(3, "Analiza sytuacji")

        mapa, regiony = svg_regiony("assets/poland.svg")
        mapa.scale_to_fit_height(5.2).to_edge(LEFT, buff=sp(128))
        ramka = naroza(mapa)

        lo, hi = min(UDZIAL_WOJEWODZTW.values()), max(UDZIAL_WOJEWODZTW.values())
        docelowe = {
            nazwa: skala_koloru(UDZIAL_WOJEWODZTW.get(nazwa, lo), lo, hi) for nazwa in regiony
        }

        # Legenda po prawej — podpisy na mapie nachodziłyby na siebie przy
        # sąsiadujących województwach.
        legenda = VGroup()
        for nazwa, tekst in PODPISY.items():
            probka = Square(
                side_length=0.28, fill_color=docelowe[nazwa], fill_opacity=1.0, stroke_width=0
            )
            opis = body(f"{tekst} — {UDZIAL_WOJEWODZTW[nazwa]}%")
            legenda.add(VGroup(probka, opis).arrange(RIGHT, buff=sp(16), aligned_edge=LEFT))
        legenda.arrange(DOWN, buff=sp(32), aligned_edge=LEFT).to_edge(RIGHT, buff=sp(96))

        with self.voiceover(text=NARRACJA) as tracker:
            self.play(wejscie(pasek), run_time=tracker.duration * 0.12)
            self.play(FadeIn(mapa), Create(ramka), run_time=tracker.duration * 0.23)
            self.play(
                *[
                    sub.animate.set_fill(docelowe[nazwa], opacity=1.0)
                    for nazwa, sub in regiony.items()
                ],
                run_time=tracker.duration * 0.35,
            )
            self.play(
                LaggedStart(*[wejscie(w) for w in legenda], lag_ratio=0.3),
                run_time=tracker.duration * 0.3,
            )

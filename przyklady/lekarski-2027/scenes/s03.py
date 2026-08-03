from dane import ROCZNIKI
from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = (
    "W 2025 maturę zdawało 256 tysięcy osób. W 2026 już 321 tysięcy. "
    "W 2027 będzie ich około 386 tysięcy."
)

SZEROKOSC = 0.62
ODSTEP = 0.28
SKALA = 0.011


class Scena_S03(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)

        pasek = pasek_misji(1, "Skala rocznika")

        podstawa = Line(LEFT * 1.9, RIGHT * 1.9, color=SIATKA, stroke_width=2)
        podstawa.shift(DOWN * 2.2)

        slupki, lata, wartosci = VGroup(), VGroup(), VGroup()
        calosc = len(ROCZNIKI) * SZEROKOSC + (len(ROCZNIKI) - 1) * ODSTEP
        start = -calosc / 2 + SZEROKOSC / 2

        for i, (rok, tys, rodzaj) in enumerate(ROCZNIKI):
            szczyt = rok == 2027
            kolor = ACCENT_3 if szczyt else (ACCENT if rodzaj == "dane" else MUTED)
            slupek = Rectangle(
                width=SZEROKOSC,
                height=tys * SKALA,
                fill_color=kolor,
                fill_opacity=1.0 if rodzaj == "dane" or szczyt else 0.45,
                stroke_width=0,
            )
            slupek.align_to(podstawa, DOWN).set_x(start + i * (SZEROKOSC + ODSTEP))
            slupki.add(slupek)

            lata.add(mono(str(rok)).next_to(slupek, DOWN, buff=sp(12)))
            wartosci.add(
                body(f"{tys}", color=kolor, font_size=skaluj(22)).next_to(slupek, UP, buff=sp(8))
            )

        jednostka = etykieta("tysięcy maturzystów")
        jednostka.next_to(podstawa, DOWN, buff=sp(48))

        prognoza = mono("PROGNOZA", color=MUTED)
        prognoza.next_to(slupki[2], UP, buff=sp(48))

        with self.voiceover(text=NARRACJA) as tracker:
            self.play(wejscie(pasek), Create(podstawa), run_time=tracker.duration * 0.15)
            self.play(
                LaggedStart(*[GrowFromEdge(s, DOWN) for s in slupki], lag_ratio=0.35),
                run_time=tracker.duration * 0.45,
            )
            self.play(
                FadeIn(lata), FadeIn(wartosci), FadeIn(jednostka),
                run_time=tracker.duration * 0.2,
            )
            self.play(
                FadeIn(prognoza, shift=DOWN * sp(8)),
                Indicate(slupki[2], color=ACCENT_3, scale_factor=1.05),
                run_time=tracker.duration * 0.2,
            )

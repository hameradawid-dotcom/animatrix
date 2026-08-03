from dane import PUM_PROGI
from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = (
    "I uwaga, bo próg wcale nie rośnie równo. "
    "Sto pięćdziesiąt osiem, potem sto czterdzieści trzy, potem sto czterdzieści dziewięć."
)

Y_MIN, Y_MAX = 135, 165


class Scena_S05(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)

        pasek = pasek_misji(3, "Próg PUM lekarski")

        os_x = Line(LEFT * 1.6, RIGHT * 1.6, color=SIATKA, stroke_width=2).shift(DOWN * 1.9)
        wysokosc = 3.2

        def punkt_y(pkt: int) -> float:
            return os_x.get_y() + (pkt - Y_MIN) / (Y_MAX - Y_MIN) * wysokosc

        najnizszy = min(range(len(PUM_PROGI)), key=lambda i: PUM_PROGI[i][1])

        wezly, etykiety_lat, wartosci = [], VGroup(), VGroup()
        for i, (rok, pkt, _) in enumerate(PUM_PROGI):
            x = -1.25 + i * 1.25
            wezly.append(np.array([x, punkt_y(pkt), 0.0]))
            etykiety_lat.add(mono(str(rok)).move_to([x, os_x.get_y() - sp(32), 0]))
            # Etykieta dołka idzie POD punkt — nad nim wpadałaby na łamaną.
            kolor = WARN if i == najnizszy else ACCENT
            odsun = -sp(64) if i == najnizszy else sp(48)
            wartosci.add(
                body(str(pkt), color=kolor, font_size=skaluj(30)).move_to(
                    [x, punkt_y(pkt) + odsun, 0]
                )
            )

        lamana = VMobject(color=ACCENT, stroke_width=6).set_points_as_corners(wezly)
        kropki = VGroup(
            *[
                Dot(w, radius=0.09, color=WARN if i == najnizszy else ACCENT)
                for i, w in enumerate(wezly)
            ]
        )

        komentarz = body("nie rośnie\nrówno", color=WARN, font_size=skaluj(26))
        komentarz.next_to(etykiety_lat, DOWN, buff=sp(48))

        with self.voiceover(text=NARRACJA) as tracker:
            self.play(wejscie(pasek), Create(os_x), FadeIn(etykiety_lat), run_time=tracker.duration * 0.2)
            self.play(Create(lamana), run_time=tracker.duration * 0.35)
            self.play(
                LaggedStart(*[GrowFromCenter(k) for k in kropki], lag_ratio=0.3),
                FadeIn(wartosci),
                run_time=tracker.duration * 0.25,
            )
            self.play(
                FadeIn(komentarz, shift=UP * sp(12)),
                Indicate(kropki[najnizszy], color=WARN, scale_factor=1.5),
                run_time=tracker.duration * 0.2,
            )

from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = (
    "Matury poszły gorzej, a próg i tak poszedł w górę. "
    "Bo próg to nie ocena, tylko miejsce w kolejce."
)

KOLUMNY = 9
WIERSZE = 11


class Scena_S08(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)

        pasek = pasek_misji(6, "Mechanika progu")

        kropki = VGroup()
        for w in range(WIERSZE):
            for k in range(KOLUMNY):
                kropki.add(Dot(radius=0.10, color=MUTED, fill_opacity=0.55))
        kropki.arrange_in_grid(rows=WIERSZE, cols=KOLUMNY, buff=sp(32))
        kropki.move_to(DOWN * 0.3)

        prog = Line(
            kropki.get_left() + LEFT * sp(24),
            kropki.get_right() + RIGHT * sp(24),
            color=ACCENT_3,
            stroke_width=4,
        )
        # Próg musi leżeć MIĘDZY wierszami kropek, a nie nad ich bounding boxem —
        # inaczej po żadnej stronie nie ma nikogo.
        krok = kropki[0].get_y() - kropki[KOLUMNY].get_y()
        prog.set_y(kropki[0].get_y() - krok * 2.5)
        opis_prog = mono("PRÓG", color=ACCENT_3).next_to(prog, UP, buff=sp(8)).align_to(prog, RIGHT)

        def nad_progiem(y: float) -> list:
            return [d for d in kropki if d.get_y() > y]

        docelowy_y = kropki[0].get_y() - krok * 1.5
        puenta = body("liczy się,\nilu ma lepiej", color=FG, font_size=skaluj(26))
        puenta.next_to(kropki, DOWN, buff=sp(48))

        with self.voiceover(text=NARRACJA) as tracker:
            self.play(wejscie(pasek), run_time=tracker.duration * 0.12)
            self.play(
                LaggedStart(*[GrowFromCenter(d) for d in kropki], lag_ratio=0.004),
                run_time=tracker.duration * 0.3,
            )
            self.play(Create(prog), FadeIn(opis_prog), run_time=tracker.duration * 0.13)
            przyjeci = nad_progiem(prog.get_y())
            self.play(
                *[d.animate.set_color(ACCENT).set_fill(opacity=1.0) for d in przyjeci],
                run_time=tracker.duration * 0.15,
            )
            self.play(
                prog.animate.set_y(docelowy_y),
                opis_prog.animate.set_y(docelowy_y),
                run_time=tracker.duration * 0.2,
                rate_func=rate_functions.ease_in_out_cubic,
            )
            odpadli = [d for d in przyjeci if d.get_y() < docelowy_y]
            self.play(
                *[d.animate.set_color(WARN).set_fill(opacity=0.4) for d in odpadli],
                FadeIn(puenta),
                run_time=tracker.duration * 0.1,
            )

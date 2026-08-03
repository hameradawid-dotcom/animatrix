from pathlib import Path

from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = "Ale próg na studia liczy się z twojego wyniku, nie z cudzego. Reszta to już czysta chemia."

PLIK_MOL = "assets/etanol.mol"


class Scena_S05(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)

        czasteczka = self._czasteczka()
        czasteczka.scale_to_fit_height(2.2).set_color(FG)

        formula = wzor(r"\mathrm{C_2H_5OH}", font_size=48, color=ACCENT)
        puenta = body("Twój wynik, nie cudzy")

        uklad = VGroup(czasteczka, formula, puenta).arrange(DOWN, buff=0.7).move_to(ORIGIN)

        with self.voiceover(text=NARRACJA) as tracker:
            self.play(Create(czasteczka), run_time=tracker.duration * 0.4)
            self.play(Write(formula), run_time=tracker.duration * 0.3)
            self.play(FadeIn(puenta, shift=UP * 0.25), run_time=tracker.duration * 0.3)

    def _czasteczka(self) -> VMobject:
        if Path(PLIK_MOL).exists():
            from manim_chemistry import MMoleculeObject

            return MMoleculeObject.from_mol_file(PLIK_MOL)
        return wzor(r"\mathrm{C_2H_5OH}", font_size=64)

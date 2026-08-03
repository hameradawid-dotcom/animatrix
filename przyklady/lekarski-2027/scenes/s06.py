from dane import PUM_LISTY_2026, PUM_PROG_2026_SZAC
from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = (
    "W tej rekrutacji pierwsza lista pokazała sto siedemdziesiąt pięć. "
    "Po trzech turach zeszła do stu sześćdziesięciu trzech."
)


class Scena_S06(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)

        pasek = pasek_misji(4, "Rekrutacja 2026")

        schodki = VGroup()
        for i, (nr, pkt) in enumerate(PUM_LISTY_2026):
            opis = mono(f"LISTA {nr}")
            wartosc = body(str(pkt), color=ACCENT, font_size=skaluj(40))
            wiersz = VGroup(opis, wartosc).arrange(RIGHT, buff=sp(24))
            wiersz.shift(RIGHT * (0.55 - i * 0.55) + DOWN * i * 0.95)
            schodki.add(wiersz)
        schodki.move_to(UP * 0.7)

        szac = VGroup(
            mono("SZACOWANY PRÓG KOŃCOWY", color=ACCENT_3),
            body(f"~{PUM_PROG_2026_SZAC}", color=ACCENT_3, font_size=skaluj(40)),
        ).arrange(DOWN, buff=sp(12))
        szac.next_to(schodki, DOWN, buff=sp(64))
        ramka = naroza(szac, kolor=ACCENT_3, margines=24, dlugosc=0.22)

        with self.voiceover(text=NARRACJA) as tracker:
            self.play(wejscie(pasek), run_time=tracker.duration * 0.12)
            self.play(
                LaggedStart(
                    *[FadeIn(w, shift=DOWN * sp(16)) for w in schodki], lag_ratio=0.45
                ),
                run_time=tracker.duration * 0.5,
            )
            self.play(FadeIn(szac), Create(ramka), run_time=tracker.duration * 0.28)
            self.play(Indicate(szac, color=ACCENT_3, scale_factor=1.08), run_time=tracker.duration * 0.1)

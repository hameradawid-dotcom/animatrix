from dane import PUM_KANDYDATOW, PUM_MIEJSC, PUM_NA_MIEJSCE
from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = (
    "Dwieście pięćdziesiąt pięć miejsc. Pięć tysięcy dwustu kandydatów. "
    "Tak wyglądał lekarski w Szczecinie w tej rekrutacji."
)


class Scena_S01(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)

        t_miejsca = ValueTracker(0)
        t_kandydaci = ValueTracker(0)
        t_ratio = ValueTracker(0)

        miejsca = licznik(t_miejsca, rozmiar=skaluj(96), kolor=ACCENT, docelowa=PUM_MIEJSC)
        kandydaci = licznik(t_kandydaci, rozmiar=skaluj(96), kolor=WARN, docelowa=PUM_KANDYDATOW)

        blok_m = VGroup(miejsca, mono("MIEJSC")).arrange(DOWN, buff=sp(8))
        blok_k = VGroup(kandydaci, mono("KANDYDATÓW")).arrange(DOWN, buff=sp(8))
        kreska = linia(2.4)
        uklad = VGroup(blok_m, kreska, blok_k).arrange(DOWN, buff=sp(32))
        uklad.move_to(UP * 1.1)

        ratio = licznik(
            t_ratio, liczba_cyfr=1, rozmiar=skaluj(72), kolor=ACCENT_3, docelowa=PUM_NA_MIEJSCE
        )
        opis = body("kandydatów\nna jedno miejsce", font_size=skaluj(24))
        stopka = VGroup(ratio, opis).arrange(DOWN, buff=sp(16))
        stopka.next_to(uklad, DOWN, buff=sp(64))

        with self.voiceover(text=NARRACJA) as tracker:
            self.add(miejsca, kandydaci)
            self.play(
                FadeIn(blok_m[1]),
                t_miejsca.animate.set_value(PUM_MIEJSC),
                run_time=tracker.duration * 0.28,
                rate_func=rate_functions.ease_out_cubic,
            )
            self.play(Create(kreska), run_time=tracker.duration * 0.07)
            self.play(
                FadeIn(blok_k[1]),
                t_kandydaci.animate.set_value(PUM_KANDYDATOW),
                run_time=tracker.duration * 0.3,
                rate_func=rate_functions.ease_out_cubic,
            )
            self.add(ratio)
            self.play(
                FadeIn(opis),
                t_ratio.animate.set_value(PUM_NA_MIEJSCE),
                run_time=tracker.duration * 0.25,
                rate_func=rate_functions.ease_out_cubic,
            )
            self.play(
                Indicate(ratio, color=ACCENT_3, scale_factor=1.12),
                run_time=tracker.duration * 0.1,
            )

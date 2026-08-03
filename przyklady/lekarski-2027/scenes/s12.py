from dane import CEL_PROC_2027, PUM_CEL_2027_SZAC, PUM_MAX_PKT
from manim_voiceover import VoiceoverScene
from theme import *

NARRACJA = (
    "Realny cel na Szczecin w 2027 to około stu siedemdziesięciu punktów. "
    "Osiemdziesiąt pięć procent z dwóch rozszerzeń."
)


class Scena_S12(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)

        pasek = pasek_misji(10, "Cel")

        t_pkt = ValueTracker(0)
        cel = licznik(t_pkt, rozmiar=skaluj(110), kolor=ACCENT_3, docelowa=PUM_CEL_2027_SZAC)
        z_ilu = mono(f"/ {PUM_MAX_PKT} PKT")
        blok = VGroup(cel, z_ilu).arrange(DOWN, buff=sp(12))
        blok.move_to(UP * 0.9)
        ramka = naroza(blok, kolor=ACCENT_3, margines=48)

        proc = body(f"{CEL_PROC_2027}%\nz chemii i biologii", font_size=skaluj(28))
        proc.next_to(blok, DOWN, buff=sp(96))

        zastrzezenie = mono("SZACUNEK\nNA PODSTAWIE DYNAMIKI 2025→2026", color=MUTED)
        zastrzezenie.scale(0.62).next_to(proc, DOWN, buff=sp(32))

        with self.voiceover(text=NARRACJA) as tracker:
            self.play(wejscie(pasek), run_time=tracker.duration * 0.12)
            self.add(cel)
            self.play(
                FadeIn(z_ilu),
                t_pkt.animate.set_value(PUM_CEL_2027_SZAC),
                run_time=tracker.duration * 0.38,
                rate_func=rate_functions.ease_out_cubic,
            )
            self.play(Create(ramka), run_time=tracker.duration * 0.15)
            self.play(FadeIn(proc, shift=UP * sp(12)), run_time=tracker.duration * 0.2)
            self.play(FadeIn(zastrzezenie), run_time=tracker.duration * 0.15)

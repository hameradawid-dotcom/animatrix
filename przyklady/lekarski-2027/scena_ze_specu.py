"""Uniwersalna scena budowana ze specu YAML.

Plik należy do narzędzia, nie do Ciebie — `animatrix` nadpisuje go przy każdym
uruchomieniu. Edytuj `sceny/sNN.yaml`, a jeśli szablon nie wystarcza, przełącz
scenę na `szablon: kod` i napisz własną klasę w `scenes/`.
"""

from manim_voiceover import VoiceoverScene

from theme import *  # noqa: F401,F403  (musi być przed budową kompozycji: ustawia config)

from animatrix.szablony.odtwarzacz import odegraj


class ScenaZeSpecu(VoiceoverScene):
    def construct(self):
        self.set_speech_service(speech_service(), create_subcaption=False)
        odegraj(self)

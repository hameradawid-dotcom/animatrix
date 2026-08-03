from animatrix.models import Costs, Script, ScriptMeta, Segment, scene_class_name


def test_nazwa_klasy_sceny():
    assert scene_class_name("s01") == "Scena_S01"
    assert scene_class_name("s-12") == "Scena_S12"


def test_koszty_licza_znaki_per_segment():
    costs = Costs()
    costs.zapisz_narracje("s01", "abc")
    costs.zapisz_narracje("s02", "abcde")
    assert costs.elevenlabs_znaki == 8
    assert costs.elevenlabs_znaki_historycznie == 0


def test_ponowny_zapis_tej_samej_narracji_nie_dublije_licznika():
    costs = Costs()
    costs.zapisz_narracje("s01", "abc")
    costs.zapisz_narracje("s01", "abc")
    assert costs.elevenlabs_znaki == 3
    assert costs.elevenlabs_znaki_historycznie == 0


def test_zmiana_narracji_przenosi_stara_wersje_do_historii():
    costs = Costs()
    costs.zapisz_narracje("s01", "abc")
    costs.zapisz_narracje("s01", "abcdef")
    assert costs.elevenlabs_znaki == 6
    assert costs.elevenlabs_znaki_historycznie == 3


def test_script_approved_wymaga_kompletu():
    script = Script(
        meta=ScriptMeta(temat="x"),
        segmenty=[Segment(id="s01", narracja="a"), Segment(id="s02", narracja="b")],
    )
    assert not script.approved
    script.segmenty[0].status = "approved"
    assert not script.approved
    script.segmenty[1].status = "approved"
    assert script.approved


def test_pusty_scenariusz_nie_jest_approved():
    assert not Script(meta=ScriptMeta(temat="x")).approved

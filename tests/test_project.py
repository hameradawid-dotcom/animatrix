import pytest

from animatrix.models import ScriptMeta, Segment
from animatrix.project import Project, ProjectError, slugify


def test_slugify_usuwa_polskie_znaki():
    assert slugify("Duży rocznik  a matura") == "duzy-rocznik-a-matura"
    assert slugify("!!!") == "projekt"


def test_create_zaklada_strukture_i_runtime(projekty):
    proj = Project.create("Test Projekt", ScriptMeta(temat="chemia"))
    assert proj.root == projekty / "test-projekt"
    for sciezka in (proj.scenes_dir, proj.previews_dir, proj.assets_dir, proj.voice_cache_dir):
        assert sciezka.is_dir()
    assert proj.theme_path.exists()
    assert (proj.root / "voice.py").exists()
    assert proj.load_script().meta.temat == "chemia"


def test_create_dwa_razy_odmawia(projekty):
    Project.create("x", ScriptMeta(temat="a"))
    with pytest.raises(ProjectError):
        Project.create("x", ScriptMeta(temat="a"))


def test_open_nieistniejacego_rzuca(projekty):
    with pytest.raises(ProjectError):
        Project.open("nie-ma-takiego")


def test_roundtrip_yaml_zachowuje_polskie_znaki(projekty):
    proj = Project.create("x", ScriptMeta(temat="stężenie"))
    script = proj.load_script()
    script.segmenty = [Segment(id="s01", narracja="Zażółć gęślą jaźń")]
    proj.save_script(script)

    surowe = proj.script_path.read_text(encoding="utf-8")
    assert "Zażółć gęślą jaźń" in surowe  # allow_unicode=True, nie ż...

    znowu = Project.open("x").load_script()
    assert znowu.segmenty[0].narracja == "Zażółć gęślą jaźń"
    assert znowu.meta.temat == "stężenie"


def test_install_runtime_nie_nadpisuje_bez_force(projekty):
    proj = Project.create("x", ScriptMeta(temat="a"))
    proj.theme_path.write_text("# moje zmiany\n", encoding="utf-8")

    assert proj.install_runtime() == []
    assert proj.theme_path.read_text(encoding="utf-8") == "# moje zmiany\n"

    assert "theme.py" in proj.install_runtime(force=True)
    assert "moje zmiany" not in proj.theme_path.read_text(encoding="utf-8")


def test_list_all_widzi_tylko_projekty_ze_scenariuszem(projekty):
    Project.create("a", ScriptMeta(temat="a"))
    (projekty / "smieci").mkdir()
    assert Project.list_all() == ["a"]

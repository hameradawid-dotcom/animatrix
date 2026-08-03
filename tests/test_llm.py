import json
from types import SimpleNamespace

import pytest

from animatrix.llm import LLM, LLMError, extract_code


def test_extract_code_bierze_najdluzszy_blok():
    tekst = "Wstęp\n```python\nx = 1\n```\ntekst\n```python\nfrom theme import *\ny = 2\n```\n"
    assert extract_code(tekst).strip() == "from theme import *\ny = 2"


def test_extract_code_akceptuje_goly_kod():
    assert extract_code("from theme import *\n").startswith("from theme import *")


def test_extract_code_bez_kodu_rzuca():
    with pytest.raises(LLMError):
        extract_code("Nie mam pomysłu na tę scenę.")


def _fake_response(text: str, stop_reason: str = "end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=11, output_tokens=22),
    )


def _llm(monkeypatch, response, zebrane=None):
    llm = LLM(on_usage=(lambda i, o: zebrane.append((i, o))) if zebrane is not None else None)
    monkeypatch.setattr(llm.client.messages, "create", lambda **kw: response)
    return llm


def test_json_call_parsuje_i_ksieguje_tokeny(projekty, monkeypatch):
    zebrane: list[tuple[int, int]] = []
    llm = _llm(monkeypatch, _fake_response(json.dumps({"narracja": "Cześć"})), zebrane)
    assert llm.json_call("sys", "user", {"type": "object"}) == {"narracja": "Cześć"}
    assert zebrane == [(11, 22)]


def test_json_call_na_odmowie_rzuca(projekty, monkeypatch):
    llm = _llm(monkeypatch, _fake_response("", stop_reason="refusal"))
    with pytest.raises(LLMError, match="odmówił"):
        llm.json_call("sys", "user", {"type": "object"})


def test_json_call_na_uciecie_rzuca(projekty, monkeypatch):
    llm = _llm(monkeypatch, _fake_response('{"a":', stop_reason="max_tokens"))
    with pytest.raises(LLMError, match="ucięta"):
        llm.json_call("sys", "user", {"type": "object"})


def test_json_call_na_smieciach_rzuca(projekty, monkeypatch):
    llm = _llm(monkeypatch, _fake_response("to nie jest json"))
    with pytest.raises(LLMError, match="JSON"):
        llm.json_call("sys", "user", {"type": "object"})


def test_brak_klucza_rzuca(monkeypatch):
    from animatrix.config import settings

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("animatrix.config._load_env", lambda: None)
    settings.cache_clear()
    try:
        with pytest.raises(LLMError, match="ANTHROPIC_API_KEY"):
            LLM()
    finally:
        settings.cache_clear()

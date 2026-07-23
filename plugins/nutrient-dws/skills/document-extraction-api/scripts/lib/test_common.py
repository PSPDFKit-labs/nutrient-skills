#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest>=8.0"]
# ///

import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import common


def _clear_keys(monkeypatch):
    monkeypatch.delenv("NUTRIENT_EXTRACT_API_KEY", raising=False)
    monkeypatch.delenv("NUTRIENT_API_KEY", raising=False)


def test_resolve_extract_key_prefers_extract_key(monkeypatch):
    monkeypatch.setenv("NUTRIENT_EXTRACT_API_KEY", "extract-key")
    monkeypatch.setenv("NUTRIENT_API_KEY", "fallback-key")

    assert common.resolve_extract_key() == "extract-key"


def test_resolve_extract_key_uses_fallback(monkeypatch):
    _clear_keys(monkeypatch)
    monkeypatch.setenv("NUTRIENT_API_KEY", "fallback-key")

    assert common.resolve_extract_key() == "fallback-key"


def test_resolve_extract_key_raises_when_both_unset(monkeypatch):
    _clear_keys(monkeypatch)

    with pytest.raises(RuntimeError, match="NUTRIENT_EXTRACT_API_KEY is not set"):
        common.resolve_extract_key()


def test_resolve_extract_key_raises_when_extract_key_is_empty(monkeypatch):
    monkeypatch.setenv("NUTRIENT_EXTRACT_API_KEY", "")
    monkeypatch.setenv("NUTRIENT_API_KEY", "fallback-key")

    with pytest.raises(RuntimeError, match="is set but empty"):
        common.resolve_extract_key()


def test_create_client_uses_resolved_key(monkeypatch):
    calls = []

    class FakeNutrientClient:
        def __init__(self, **kwargs):
            calls.append(kwargs)

    fake_module = types.ModuleType("nutrient_dws")
    fake_module.NutrientClient = FakeNutrientClient
    monkeypatch.setitem(sys.modules, "nutrient_dws", fake_module)
    monkeypatch.setenv("NUTRIENT_EXTRACT_API_KEY", "extract-key")
    monkeypatch.setenv("NUTRIENT_API_KEY", "fallback-key")

    common.create_client()

    assert calls == [
        {"api_key": "extract-key", "extract_api_key": "extract-key"}
    ]


def test_create_client_raises_when_extract_key_is_empty(monkeypatch):
    monkeypatch.setenv("NUTRIENT_EXTRACT_API_KEY", "")
    monkeypatch.setenv("NUTRIENT_API_KEY", "fallback-key")

    with pytest.raises(RuntimeError, match="is set but empty"):
        common.create_client()


def test_redact_replaces_key_everywhere():
    assert (
        common.redact("key-secret then key-secret again", "key-secret")
        == "[REDACTED] then [REDACTED] again"
    )


@pytest.mark.parametrize("key", [None, "not-present"])
def test_redact_is_noop_when_key_is_none_or_absent(key):
    text = "safe error text"

    assert common.redact(text, key) == text


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

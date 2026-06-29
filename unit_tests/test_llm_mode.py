"""BFRAME_0031 — full LLM mode toggle + provider-agnostic api_base.

No live model and no browser: _llm_resolve is monkeypatched to a sentinel, so we
assert *routing* (does full mode skip patterns?) without a network call.
"""
import pytest

from bddframe.resolver import step_resolver
from bddframe.llm import client


# --- BDDFRAME_LLM_MODE routing ------------------------------------------------

def _spy_llm(monkeypatch):
    """Replace _llm_resolve with a sentinel-returning spy; returns the call log."""
    calls = []

    def fake(step_text):
        calls.append(step_text)
        return {"type": "click", "locator": "spy"}

    monkeypatch.setattr(step_resolver, "_llm_resolve", fake)
    return calls


def test_auto_mode_matches_pattern_without_calling_llm(monkeypatch):
    monkeypatch.delenv("BDDFRAME_LLM_MODE", raising=False)
    monkeypatch.setenv("BDDFRAME_MODEL", "anything")  # set, but must NOT be used
    calls = _spy_llm(monkeypatch)

    action = step_resolver.resolve("User clicks the login button")

    assert action == {"type": "click", "locator": "login"}
    assert calls == []  # pattern matched → LLM never consulted


def test_full_mode_skips_patterns_and_calls_llm(monkeypatch):
    monkeypatch.setenv("BDDFRAME_LLM_MODE", "full")
    monkeypatch.setenv("BDDFRAME_MODEL", "anthropic/claude-sonnet-4-6")
    calls = _spy_llm(monkeypatch)

    # This step WOULD match the click pattern in auto mode — full mode must still
    # route it to the LLM.
    action = step_resolver.resolve("User clicks the login button")

    assert action == {"type": "click", "locator": "spy"}
    assert calls == ["User clicks the login button"]


def test_full_mode_without_model_raises_clear_error(monkeypatch):
    monkeypatch.setenv("BDDFRAME_LLM_MODE", "full")
    monkeypatch.delenv("BDDFRAME_MODEL", raising=False)

    with pytest.raises(AssertionError, match="BDDFRAME_LLM_MODE=full but BDDFRAME_MODEL is not set"):
        step_resolver.resolve("User clicks the login button")


def test_full_mode_resolves_rest_steps(monkeypatch):
    monkeypatch.setenv("BDDFRAME_LLM_MODE", "full")
    monkeypatch.setenv("BDDFRAME_MODEL", "gemini/gemini-1.5-flash")
    calls = _spy_llm(monkeypatch)

    step_resolver.resolve("performs a POST call at '/users' with body '{}'")

    assert calls == ["performs a POST call at '/users' with body '{}'"]


# --- provider-agnostic api_base (the "support ALL LLMs" fix) -------------------

def test_api_base_is_none_when_url_unset(monkeypatch):
    """Cloud providers (Anthropic/Gemini/Groq/OpenAI) must NOT get a hardcoded
    Ollama localhost base — that silently misroutes them. Unset → None."""
    monkeypatch.delenv("BDDFRAME_LLM_URL", raising=False)
    assert client._api_base() is None


def test_api_base_passes_through_explicit_url(monkeypatch):
    """Ollama / Foundry Local / self-hosted still get their endpoint."""
    monkeypatch.setenv("BDDFRAME_LLM_URL", "http://localhost:11434")
    assert client._api_base() == "http://localhost:11434"

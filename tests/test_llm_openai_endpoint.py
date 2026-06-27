"""Smoke test: bddframe -> LiteLLM -> an OpenAI-compatible local endpoint.

This is the contract bddframe relies on to run against Foundry Local (or any
OpenAI-compatible local server) on a network where Ollama/Hugging Face are
blocked. A stdlib stub stands in for the Foundry Local web service so the test
has no external dependency.

Covers:
  - client.ask() round-trips text through the endpoint.
  - step_resolver.resolve() falls back to the LLM (Trigger 1) when no regex
    pattern matches, and parses the model's JSON action.

Run just this file with logs of the model exchange:
    uv run --with litellm --with pytest python tests/test_llm_openai_endpoint.py
"""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

litellm = pytest.importorskip("litellm")  # skip if the [llm] extra isn't installed

from bddframe.llm.client import ask
from bddframe.resolver import step_resolver


class _Stub:
    """A minimal OpenAI-compatible /v1/chat/completions server (Foundry stand-in)."""

    def __init__(self):
        self.reply = "ok"          # set by each test to whatever the "model" should say
        self.requests = []         # parsed request bodies, newest last
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
                stub.requests.append(body)
                out = {
                    "id": "stub", "object": "chat.completion", "model": body.get("model"),
                    "choices": [{"index": 0, "finish_reason": "stop",
                                 "message": {"role": "assistant", "content": stub.reply}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }
                data = json.dumps(out).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self._srv = HTTPServer(("127.0.0.1", 0), Handler)
        self.endpoint = f"http://127.0.0.1:{self._srv.server_address[1]}/v1"
        threading.Thread(target=self._srv.serve_forever, daemon=True).start()

    def stop(self):
        self._srv.shutdown()

    @property
    def last_prompt(self):
        """The user prompt bddframe actually sent the model on the last call."""
        return self.requests[-1]["messages"][-1]["content"]


@pytest.fixture
def foundry(monkeypatch):
    stub = _Stub()
    # exactly the .env.example Foundry Local config (port = the stub's)
    monkeypatch.setenv("BDDFRAME_MODEL", "openai/qwen2.5-7b-instruct-generic-cpu")
    monkeypatch.setenv("BDDFRAME_LLM_URL", stub.endpoint)
    monkeypatch.setenv("OPENAI_API_KEY", "not-needed")  # LiteLLM's openai/ path requires it set
    yield stub
    stub.stop()


def test_ask_round_trips_through_the_endpoint(foundry):
    foundry.reply = "the model is reachable"
    assert ask("are you there?") == "the model is reachable"
    # bddframe sent our prompt to the endpoint
    assert foundry.last_prompt == "are you there?"


def test_resolve_falls_back_to_llm_on_no_pattern_match(foundry):
    # "submits" is not a known verb -> no regex matches -> Trigger 1 fires.
    foundry.reply = '{"type": "click", "locator": "Login"}'
    action = step_resolver.resolve("User submits the login form")
    assert action == {"type": "click", "locator": "Login"}
    # the step text bddframe asked the model to interpret reached the endpoint
    assert "submits the login form" in foundry.last_prompt


def test_unset_api_key_is_the_documented_gotcha(foundry, monkeypatch):
    # Without OPENAI_API_KEY, LiteLLM's openai/ provider errors before the call.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(Exception):
        ask("this should fail fast")


if __name__ == "__main__":
    # Verbose run: show exactly what the model received and returned for Trigger 1.
    stub = _Stub()
    os.environ.update(
        BDDFRAME_MODEL="openai/qwen2.5-7b-instruct-generic-cpu",
        BDDFRAME_LLM_URL=stub.endpoint,
        OPENAI_API_KEY="not-needed",
    )
    stub.reply = '{"type": "click", "locator": "Login"}'
    step = "User submits the login form"

    print(f"\n  endpoint (Foundry stand-in): {stub.endpoint}")
    print(f"  feature step (no regex match): {step!r}\n")
    action = step_resolver.resolve(step)

    print("  ── what bddframe SENT the model ───────────────────────────────")
    print("    " + stub.last_prompt.replace("\n", "\n    "))
    print("  ── what the model RETURNED ────────────────────────────────────")
    print(f"    {stub.reply}")
    print("  ── how bddframe USED it (parsed action) ───────────────────────")
    print(f"    {action}\n")
    assert action == {"type": "click", "locator": "Login"}
    print("  PASS: no-match step -> LLM -> parsed action.\n")
    stub.stop()

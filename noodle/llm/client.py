import os


def _litellm():
    try:
        import litellm
        return litellm
    except ImportError:
        raise ImportError("LLM support requires: pip install noodle[llm]")


def _api_base():
    """The endpoint override, or None to let LiteLLM use the provider's default.

    Only Ollama / Foundry Local / self-hosted OpenAI-compatible servers need an
    explicit base URL. Cloud providers (Anthropic, Gemini, Groq, OpenAI) resolve
    their own endpoint from the model string + API key — passing a hardcoded
    localhost base here would silently misroute them. ponytail: unset → None,
    LiteLLM fills in the right URL per provider.
    """
    return os.getenv("NOODLE_LLM_URL") or None


def ask(prompt: str) -> str:
    ll = _litellm()
    response = ll.completion(
        model=os.getenv("NOODLE_MODEL", "ollama/llama3"),
        api_base=_api_base(),
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def ask_vision(prompt: str, image_b64: str) -> str:
    """Send a text prompt + base64 screenshot to a vision-capable model."""
    ll = _litellm()
    response = ll.completion(
        model=os.getenv("NOODLE_MODEL"),
        api_base=_api_base(),
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
            ],
        }],
    )
    return response.choices[0].message.content

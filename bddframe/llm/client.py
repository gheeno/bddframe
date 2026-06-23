import os


def _litellm():
    try:
        import litellm
        return litellm
    except ImportError:
        raise ImportError("LLM support requires: pip install bddframe[llm]")


def ask(prompt: str) -> str:
    ll = _litellm()
    response = ll.completion(
        model=os.getenv("BDDFRAME_MODEL", "ollama/llama3"),
        api_base=os.getenv("BDDFRAME_LLM_URL", "http://localhost:11434"),
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def ask_vision(prompt: str, image_b64: str) -> str:
    """Send a text prompt + base64 screenshot to a vision-capable model."""
    ll = _litellm()
    response = ll.completion(
        model=os.getenv("BDDFRAME_MODEL"),
        api_base=os.getenv("BDDFRAME_LLM_URL", "http://localhost:11434"),
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
            ],
        }],
    )
    return response.choices[0].message.content

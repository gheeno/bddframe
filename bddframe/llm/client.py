import os


def ask(prompt: str) -> str:
    try:
        import litellm
    except ImportError:
        raise ImportError("LLM support requires: pip install bddframe[llm]")

    response = litellm.completion(
        model=os.getenv("BDDFRAME_MODEL", "ollama/llama3"),
        api_base=os.getenv("BDDFRAME_LLM_URL", "http://localhost:11434"),
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content

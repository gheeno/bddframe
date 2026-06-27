"""Vision LLM fallback: describe an element, get back (x, y) coords."""
import json
import os

from .screenshot import capture


def locate_by_description(description: str) -> tuple[int, int] | None:
    """Return (x, y) from vision LLM, or None if model not configured or parse fails."""
    if not os.getenv("BDDFRAME_VISION_MODEL"):
        return None

    import base64
    from bddframe.llm.client import ask_vision

    screen_pil, _ = capture()
    import io
    buf = io.BytesIO()
    screen_pil.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()

    prompt = (
        f'In this screenshot, where is: "{description}"? '
        'Reply with {"x": <int>, "y": <int>} only — the pixel coordinates of the center.'
    )
    raw = ask_vision(prompt=prompt, image_b64=b64)

    try:
        data = json.loads(raw.strip())
        return int(data["x"]), int(data["y"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None

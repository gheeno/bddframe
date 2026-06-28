"""Vision LLM fallback: describe an element, get back (x, y) coords."""
import json
import os

from .screenshot import capture


def locate_by_description(description: str, image=None) -> tuple[int, int] | None:
    """Return (x, y) from vision LLM, or None if no model is configured or the
    parse fails. `image` (PIL) is the frame to search — the web agent passes a
    browser screenshot; default captures the OS screen (desktop agent)."""
    if not (os.getenv("BDDFRAME_VISION_MODEL") or os.getenv("BDDFRAME_MODEL")):
        return None

    import base64
    from bddframe.llm.client import ask_vision

    if image is None:
        image, _ = capture()
    import io
    buf = io.BytesIO()
    image.save(buf, format="PNG")
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

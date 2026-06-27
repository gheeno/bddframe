"""Tesseract OCR wrapper for finding text on screen."""
from .screenshot import capture


def _tesseract():
    try:
        import pytesseract
        return pytesseract
    except ImportError:
        raise ImportError("Visual agent requires pytesseract: pip install bddframe[visual]")


def find_text_on_screen(text: str) -> tuple[int, int] | None:
    """Return (x, y) centroid of the first bounding box containing text, or None."""
    from PIL import Image, ImageEnhance
    pytesseract = _tesseract()

    screen_pil, _ = capture()

    # Preprocess: grayscale + contrast boost improves OCR on UI text
    gray = screen_pil.convert("L")
    enhanced = ImageEnhance.Contrast(gray).enhance(2.0)

    data = pytesseract.image_to_data(enhanced, output_type=pytesseract.Output.DICT)

    needle = text.strip().lower()
    n = len(data["text"])
    for i in range(n):
        word = (data["text"][i] or "").strip().lower()
        if not word or data["conf"][i] < 0:
            continue
        if needle in word or word in needle:
            x = data["left"][i] + data["width"][i] // 2
            y = data["top"][i] + data["height"][i] // 2
            return x, y

    return None

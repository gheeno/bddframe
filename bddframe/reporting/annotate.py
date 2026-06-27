from pathlib import Path
from PIL import Image, ImageDraw


def _annotated_path(img_path: str) -> str:
    p = Path(img_path)
    return str(p.with_stem(p.stem + "_annotated"))


def draw_not_found(img_path: str, label: str) -> str:
    """Red dashed border around the full image with label text at top-left."""
    img = Image.open(img_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    w, h = img.size
    # Dashed red border — draw in segments
    dash, gap, thickness = 12, 6, 3
    for side in ["top", "bottom", "left", "right"]:
        if side == "top":
            coords = [(x, 0, x + dash, thickness) for x in range(0, w, dash + gap)]
        elif side == "bottom":
            coords = [(x, h - thickness, x + dash, h) for x in range(0, w, dash + gap)]
        elif side == "left":
            coords = [(0, y, thickness, y + dash) for y in range(0, h, dash + gap)]
        else:
            coords = [(w - thickness, y, w, y + dash) for y in range(0, h, dash + gap)]
        for box in coords:
            draw.rectangle(box, fill="red")
    draw.text((8, 8), f"NOT FOUND: {label}", fill="red")
    out = _annotated_path(img_path)
    img.save(out)
    return out


def draw_assertion_failure(img_path: str, label: str) -> str:
    """Semi-transparent yellow overlay with red ✗ and label text."""
    img = Image.open(img_path).convert("RGBA")
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (255, 255, 0, 60))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)
    draw.text((8, 8), f"✗ ASSERTION FAILED: {label}", fill="red")
    out = _annotated_path(img_path)
    img.convert("RGB").save(out)
    return out


def draw_timeout(img_path: str, label: str) -> str:
    """Orange TIMEOUT text overlay."""
    img = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw.text((8, 8), f"TIMEOUT: {label}", fill="orange")
    out = _annotated_path(img_path)
    img.save(out)
    return out

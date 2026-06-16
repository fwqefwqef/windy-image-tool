from __future__ import annotations

import io
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

MEME_FONTS = {
    "Impact": "impact.ttf",
    "Arial": "arial.ttf",
    "Arial Bold": "arialbd.ttf",
    "Comic Sans MS": "comic.ttf",
    "Times New Roman": "times.ttf",
    "Courier New": "cour.ttf",
    "Verdana": "verdana.ttf",
}

FORMAT_EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "AVIF": ".avif",
    "BMP": ".bmp",
    "GIF": ".gif",
    "TIFF": ".tiff",
}

SAVE_KWARGS = {
    "JPEG": {"quality": 95, "optimize": True},
    "PNG": {"optimize": True},
    "WEBP": {"quality": 90, "method": 6},
    "AVIF": {"quality": 80},
    "BMP": {},
    "GIF": {"optimize": True},
    "TIFF": {"compression": "tiff_deflate"},
}


def ensure_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_image(path: str | Path) -> Image.Image:
    image = Image.open(path)
    image.load()
    return image


def unique_output_path(output_dir: Path, stem: str, suffix: str) -> Path:
    candidate = output_dir / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate
    index = 1
    while True:
        candidate = output_dir / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def prepare_for_format(image: Image.Image, fmt: str) -> Image.Image:
    if fmt in {"JPEG", "BMP"} and image.mode not in {"RGB", "L"}:
        return image.convert("RGB")
    if fmt == "GIF" and image.mode not in {"P", "L", "RGB"}:
        return image.convert("P", palette=Image.ADAPTIVE)
    return image


def save_image(image: Image.Image, path: Path, fmt: str, **extra_kwargs) -> None:
    prepared = prepare_for_format(image, fmt)
    kwargs = dict(SAVE_KWARGS.get(fmt, {}))
    kwargs.update(extra_kwargs)
    prepared.save(path, format=fmt, **kwargs)


def convert_image(
    source_path: str | Path,
    output_dir: str | Path,
    target_format: str,
) -> Path:
    output_path = ensure_output_dir(output_dir)
    image = load_image(source_path)
    suffix = FORMAT_EXTENSIONS[target_format]
    stem = Path(source_path).stem + "_converted"
    destination = unique_output_path(output_path, stem, suffix)
    save_image(image, destination, target_format)
    return destination


def crop_image(
    source_path: str | Path,
    output_dir: str | Path,
    x: int,
    y: int,
    width: int,
    height: int,
) -> Path:
    output_path = ensure_output_dir(output_dir)
    image = load_image(source_path)
    box = (
        max(0, x),
        max(0, y),
        min(image.width, x + width),
        min(image.height, y + height),
    )
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError("Crop bounds are invalid.")
    cropped = image.crop(box)
    suffix = Path(source_path).suffix.lower() or ".png"
    destination = unique_output_path(output_path, f"{Path(source_path).stem}_cropped", suffix)
    cropped.save(destination)
    return destination


def resize_image(
    source_path: str | Path,
    output_dir: str | Path,
    width: int,
    height: int,
) -> Path:
    output_path = ensure_output_dir(output_dir)
    image = load_image(source_path)
    resized = image.resize((width, height), Image.Resampling.LANCZOS)
    suffix = Path(source_path).suffix.lower() or ".png"
    destination = unique_output_path(output_path, f"{Path(source_path).stem}_resized", suffix)
    resized.save(destination)
    return destination


def _save_to_buffer(image: Image.Image, fmt: str, quality: int) -> bytes:
    buffer = io.BytesIO()
    prepared = prepare_for_format(image, fmt)
    kwargs = dict(SAVE_KWARGS.get(fmt, {}))
    if fmt in {"JPEG", "WEBP", "AVIF"}:
        kwargs["quality"] = quality
    prepared.save(buffer, format=fmt, **kwargs)
    return buffer.getvalue()


def _pick_compress_format(source_path: Path) -> str:
    ext = source_path.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        return "JPEG"
    if ext == ".webp":
        return "WEBP"
    if ext == ".avif":
        return "AVIF"
    if ext == ".png":
        return "WEBP"
    return "JPEG"


def _save_like_source(image: Image.Image, source_path: str | Path, output_dir: str | Path, tag: str) -> Path:
    output_path = ensure_output_dir(output_dir)
    suffix = Path(source_path).suffix.lower() or ".png"
    destination = unique_output_path(output_path, f"{Path(source_path).stem}_{tag}", suffix)
    if suffix in {".jpg", ".jpeg"}:
        save_image(image, destination, "JPEG")
    else:
        image.save(destination)
    return destination


def rotate_image(
    source_path: str | Path,
    output_dir: str | Path,
    degrees: int,
    direction: str,
) -> Path:
    image = load_image(source_path)
    if degrees == 180:
        rotated = image.transpose(Image.Transpose.ROTATE_180)
    elif degrees == 90:
        if direction == "right":
            rotated = image.transpose(Image.Transpose.ROTATE_270)
        else:
            rotated = image.transpose(Image.Transpose.ROTATE_90)
    elif degrees == 270:
        if direction == "right":
            rotated = image.transpose(Image.Transpose.ROTATE_90)
        else:
            rotated = image.transpose(Image.Transpose.ROTATE_270)
    else:
        raise ValueError("Rotation must be 90, 180, or 270 degrees.")
    return _save_like_source(rotated, source_path, output_dir, f"rotated_{degrees}{direction[0]}")


def flip_image(
    source_path: str | Path,
    output_dir: str | Path,
    axis: str,
) -> Path:
    image = load_image(source_path)
    if axis == "horizontal":
        flipped = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        tag = "flipped_h"
    elif axis == "vertical":
        flipped = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        tag = "flipped_v"
    else:
        raise ValueError("Flip axis must be horizontal or vertical.")
    return _save_like_source(flipped, source_path, output_dir, tag)


def shift_hue(image: Image.Image, degrees: float) -> Image.Image:
    if degrees % 360 == 0:
        return image.copy()

    has_alpha = image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info)
    if image.mode == "RGBA":
        rgb = image.convert("RGB")
        alpha = image.split()[3]
    elif image.mode == "LA":
        rgb = image.convert("RGB")
        alpha = image.split()[1]
    else:
        rgb = image.convert("RGB")
        alpha = None

    hsv = rgb.convert("HSV")
    h, s, v = hsv.split()
    shift = int(round((degrees % 360) / 360 * 255)) % 256
    shifted_h = h.point(lambda value: (value + shift) % 256)
    result = Image.merge("HSV", (shifted_h, s, v)).convert("RGB")

    if alpha is not None:
        result = result.convert("RGBA")
        result.putalpha(alpha)
    elif has_alpha and image.mode == "P":
        result = result.convert("P", palette=Image.ADAPTIVE)

    return result


def adjust_hue_image(
    source_path: str | Path,
    output_dir: str | Path,
    degrees: float,
) -> Path:
    image = load_image(source_path)
    adjusted = shift_hue(image, degrees)
    return _save_like_source(adjusted, source_path, output_dir, "hue")


def compress_image(
    source_path: str | Path,
    output_dir: str | Path,
    target_kb: int | None = None,
) -> tuple[Path, int]:
    output_path = ensure_output_dir(output_dir)
    source = Path(source_path)
    image = load_image(source)
    fmt = _pick_compress_format(source)
    suffix = FORMAT_EXTENSIONS[fmt]

    original_size = os.path.getsize(source)
    if target_kb is None:
        target_bytes = max(32 * 1024, int(original_size * 0.7))
    else:
        target_bytes = max(16 * 1024, target_kb * 1024)

    best_quality = 85
    best_data = _save_to_buffer(image, fmt, best_quality)
    if len(best_data) <= target_bytes:
        destination = unique_output_path(output_path, f"{source.stem}_compressed", suffix)
        destination.write_bytes(best_data)
        return destination, len(best_data)

    low, high = 5, 95
    best_data = None
    while low <= high:
        mid = (low + high) // 2
        data = _save_to_buffer(image, fmt, mid)
        if len(data) <= target_bytes:
            best_quality = mid
            best_data = data
            low = mid + 1
        else:
            high = mid - 1

    if best_data is None:
        best_data = _save_to_buffer(image, fmt, 5)

    destination = unique_output_path(output_path, f"{source.stem}_compressed", suffix)
    destination.write_bytes(best_data)
    return destination, len(best_data)


def resolve_meme_font(family: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    size = max(1, int(size))
    candidates = [MEME_FONTS.get(family, family), family]
    for name in candidates:
        if not name:
            continue
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    for fallback in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(fallback, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_meme_text(
    text: str,
    font_family: str,
    font_size: float,
    fill: str,
    outline: str,
    outline_width: float,
) -> Image.Image:
    """Render a text label (with outline) onto a transparent image.

    The returned image's top-left corner is the anchor used for positioning,
    so the editor preview and the exported result stay pixel-aligned.
    """
    font = resolve_meme_font(font_family, int(round(font_size)))
    stroke = max(0, int(round(outline_width)))
    content = text if text else " "

    measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = measure.multiline_textbbox((0, 0), content, font=font, stroke_width=stroke, align="center")
    pad = stroke + 4
    width = max(1, bbox[2] - bbox[0]) + 2 * pad
    height = max(1, bbox[3] - bbox[1]) + 2 * pad

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.multiline_text(
        (pad - bbox[0], pad - bbox[1]),
        content,
        font=font,
        fill=fill,
        stroke_width=stroke,
        stroke_fill=outline,
        align="center",
    )
    return image


def compose_meme(base: Image.Image, layers: list[dict]) -> Image.Image:
    canvas = base.convert("RGBA").copy()
    for layer in layers:
        if layer["type"] == "image":
            width = max(1, int(round(layer["w"])))
            height = max(1, int(round(layer["h"])))
            overlay = layer["image"].convert("RGBA").resize((width, height), Image.Resampling.LANCZOS)
            canvas.alpha_composite(overlay, (int(round(layer["x"])), int(round(layer["y"]))))
        else:
            text_img = render_meme_text(
                layer["text"],
                layer["font"],
                layer["size"],
                layer["fill"],
                layer["outline"],
                layer["outline_width"],
            )
            canvas.alpha_composite(text_img, (int(round(layer["x"])), int(round(layer["y"]))))
    return canvas


def export_meme(
    base_path: str | Path,
    output_dir: str | Path,
    layers: list[dict],
    base_image: Image.Image | None = None,
) -> Path:
    base = base_image if base_image is not None else load_image(base_path)
    composed = compose_meme(base, layers)

    output_path = ensure_output_dir(output_dir)
    suffix = Path(base_path).suffix.lower() or ".png"
    if suffix in {".jpg", ".jpeg"}:
        fmt = "JPEG"
        composed = composed.convert("RGB")
    elif suffix == ".bmp":
        fmt = "BMP"
        composed = composed.convert("RGB")
    elif suffix == ".webp":
        fmt = "WEBP"
    else:
        suffix = ".png"
        fmt = "PNG"

    destination = unique_output_path(output_path, f"{Path(base_path).stem}_meme", suffix)
    save_image(composed, destination, fmt)
    return destination

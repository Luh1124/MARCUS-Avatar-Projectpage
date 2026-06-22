"""Clean Blender preview renders for the project page.

Some source blends carry missing texture/compositor state that can produce a
magenta render background. This script replaces that background, crops around
the rendered mesh, and writes a polished square preview image in-place.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


BACKGROUND = (237, 243, 240, 255)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--size", type=int, default=1200)
    return parser.parse_args()


def is_magenta(pixel: tuple[int, int, int, int]) -> bool:
    r, g, b, _ = pixel
    return r > 115 and b > 115 and g < 115 and abs(r - b) < 70


def is_dark_flat_background(pixel: tuple[int, int, int, int]) -> bool:
    r, g, b, _ = pixel
    return max(r, g, b) < 92 and max(r, g, b) - min(r, g, b) < 10


def differs_from_background(pixel: tuple[int, int, int, int]) -> bool:
    r, g, b, _ = pixel
    br, bg, bb, _ = BACKGROUND
    return abs(r - br) + abs(g - bg) + abs(b - bb) > 32


def neutral_preview_pixel(pixel: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    r, g, b, a = pixel
    luminance = int(0.299 * r + 0.587 * g + 0.114 * b)
    value = max(76, min(226, luminance))
    return (value, value, value, a)


def clean_image(path: Path, size: int) -> None:
    image = Image.open(path).convert("RGBA")
    pixels = image.load()
    width, height = image.size

    for y in range(height):
        for x in range(width):
            if is_magenta(pixels[x, y]) or is_dark_flat_background(pixels[x, y]):
                pixels[x, y] = BACKGROUND

    for y in range(height):
        for x in range(width):
            if differs_from_background(pixels[x, y]):
                pixels[x, y] = neutral_preview_pixel(pixels[x, y])

    keep_x: list[int] = []
    keep_y: list[int] = []
    for y in range(height):
        for x in range(width):
            if differs_from_background(pixels[x, y]):
                keep_x.append(x)
                keep_y.append(y)

    if keep_x and keep_y:
        left, right = min(keep_x), max(keep_x)
        top, bottom = min(keep_y), max(keep_y)
        pad = int(max(right - left, bottom - top) * 0.24)
        left = max(0, left - pad)
        top = max(0, top - pad)
        right = min(width, right + pad)
        bottom = min(height, bottom + pad)
        image = image.crop((left, top, right, bottom))

    target = int(size * 0.72)
    scale = target / max(image.width, image.height)
    if scale > 0:
        image = image.resize(
            (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
            Image.Resampling.LANCZOS,
        )
    canvas = Image.new("RGBA", (size, size), BACKGROUND)
    x = (size - image.width) // 2
    y = (size - image.height) // 2
    canvas.alpha_composite(image, (x, y))
    canvas.convert("RGB").save(path, quality=94)
    print(f"Processed {path}")


def main() -> None:
    args = parse_args()
    for path in args.images:
        clean_image(path, args.size)


if __name__ == "__main__":
    main()

from __future__ import annotations

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from thermal_app.application.dto import RenderOptions
from thermal_app.domain.errors import RenderingError


DITHERING_ALGORITHMS = ("threshold", "floyd-steinberg", "atkinson", "ordered-bayer")


def thermalize(image: Image.Image, options: RenderOptions) -> Image.Image:
    grayscale = image.convert("L")
    if options.brightness != 1.0:
        grayscale = ImageEnhance.Brightness(grayscale).enhance(options.brightness)
    if options.contrast != 1.0:
        grayscale = ImageEnhance.Contrast(grayscale).enhance(options.contrast)
    if options.sharpen:
        grayscale = grayscale.filter(ImageFilter.SHARPEN)
    if options.invert:
        grayscale = ImageOps.invert(grayscale)
    if options.dithering == "threshold":
        return grayscale.point(lambda value: 255 if value >= options.threshold else 0, mode="1")
    if options.dithering == "floyd-steinberg":
        return grayscale.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    if options.dithering == "atkinson":
        return _atkinson(grayscale)
    if options.dithering == "ordered-bayer":
        return _ordered_bayer(grayscale)
    raise RenderingError(f"Bilinmeyen dithering algoritması: {options.dithering}")


def _atkinson(image: Image.Image) -> Image.Image:
    width, height = image.size
    values = [float(value) for value in image.get_flattened_data()]
    output = [255] * (width * height)
    neighbors = ((1, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (0, 2))
    for y in range(height):
        for x in range(width):
            index = y * width + x
            old = values[index]
            new = 255.0 if old >= 128.0 else 0.0
            output[index] = int(new)
            error = (old - new) / 8.0
            for dx, dy in neighbors:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    neighbor_index = ny * width + nx
                    values[neighbor_index] = min(255.0, max(0.0, values[neighbor_index] + error))
    result = Image.new("L", (width, height))
    result.putdata(output)
    return result.convert("1", dither=Image.Dither.NONE)


def _ordered_bayer(image: Image.Image) -> Image.Image:
    matrix = (
        (0, 8, 2, 10),
        (12, 4, 14, 6),
        (3, 11, 1, 9),
        (15, 7, 13, 5),
    )
    width, height = image.size
    source = image.load()
    result = Image.new("1", (width, height), 1)
    target = result.load()
    for y in range(height):
        for x in range(width):
            threshold = (matrix[y % 4][x % 4] + 0.5) * 16
            target[x, y] = 255 if source[x, y] >= threshold else 0
    return result

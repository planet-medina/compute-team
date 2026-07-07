"""
ascii_converter.py

Core logic for converting an image into ASCII art.

Approach
--------
1. Resize the image down to a manageable width (ASCII art at full image
   resolution is unreadable and unnecessary, since we're going for resemblance).
2. Convert to grayscale, since brightness (not color) drives the
   character selection.
3. Map each pixel's brightness (0-255) onto a fixed ramp of characters
   ordered from "visually dense" (dark) to "visually sparse" (light),
   similar to picking a key out of an ordered lookup table.

Known limitations / assumptions
--------------------------------
- Color is discarded in favor of simplifying output such that it can be
  wrapped in a JSON response, and raw ANSI codes embedded in JSON
  strings are awkward for API clients to consume.
- A minimalist ASCII art ramp is used for character mapping; a more
  sophisticated ramp could provide finer-grained tonal detail and
  improve visual fidelity.
- Monospace fonts are taller than they are wide (roughly 2:1 in most
  terminals), so a naive resize would produce a vertically-stretched
  image. We correct for this with CHAR_ASPECT_CORRECTION.
- This is a lossy, one-way transform. There is no way to reconstruct
  the original image from the ASCII output, by design.
"""

from PIL import Image
import io

# Characters ordered from "visually darkest/densest" to "lightest/sparsest".
# This 10-character ramp is a commonly used one in ASCII art generators.
# (called the "Minimalist Ramp" in https://inkmeascii.com/blog/best-ascii-characters/)
ASCII_RAMP = "@%#*+=-:. "

# Terminal character cells are roughly twice as tall as they are wide.
# Without this correction, converted images look vertically stretched.
# (see ``What is aspect ratio correction?`` in https://theproductguy.in/blogs/image-to-ascii-guide/)
CHAR_ASPECT_CORRECTION = 0.55


def _map_pixel_to_char(brightness: int, ramp: str, invert: bool, max_brightness: int = 255) -> str:
    """
    Map a single grayscale pixel value (0-255) to a character in the ramp.

    This is conceptually the same as a Python dict lookup where the "key"
    is a brightness bucket -- e.g. `ramp[bucket_index]` -- except the
    buckets are computed on the fly from a continuous 0-255 range rather
    than being pre-defined dict keys.
    """
    if invert:
        brightness = 255 - brightness
    # Scale 0-255 down to an index into the ramp string:
    max_index = len(ramp) - 1
    brightness_norm = brightness / max_brightness
    # Now let's map the normalized pixel values to our new
    # "scale" (the ASCII ramp). We use int() to round down to the floor integer.
    index = int(brightness_norm * max_index)

    return ramp[index]


def image_to_ascii(
    image_bytes: bytes,
    width: int = 100,
    ramp: str = ASCII_RAMP,
    invert: bool = False,
) -> dict:
    """
    Convert raw image bytes into an ASCII art representation.

    Args:
        image_bytes: Raw bytes of the uploaded image file.
        width: Desired output width in characters. Height is derived
            automatically to preserve the image's aspect ratio (with
            correction for character cell shape).
        ramp: The character gradient to use, dark -> light. Callers can
            supply a custom ramp (e.g. a shorter/simpler one) if desired.
        invert: If True, flips the brightness mapping. Useful for images
            that will be displayed on a dark-background terminal versus
            a light background.

    Returns:
        A dict with the ascii art string and metadata about the output
        dimensions, ready to be JSON-serialized by the caller.

    Raises:
        ValueError: if the bytes cannot be parsed as an image, or width
            is not a positive integer.
    """
    if width <= 0:
        raise ValueError("width must be a positive integer")
    if not ramp:
        raise ValueError("ramp must be a non-empty string")

    try:
        image = Image.open(io.BytesIO(image_bytes))
        # .load() forces PIL to actually decode the image now, so that
        # any truncation/corruption errors surface here with a clear
        # error rather than later during resize/convert.
        image.load()
    except Exception as exc:
        raise ValueError(f"Could not read image: {exc}") from exc

    # Derive a proportional height, corrected for character cell aspect ratio.
    original_width, original_height = image.size
    aspect_ratio = original_height / original_width
    height = max(1, int(aspect_ratio * width * CHAR_ASPECT_CORRECTION))

    # Resize and flatten to grayscale ("L" mode = single 0-255 luminance channel).
    resized = image.resize((width, height))
    grayscale = resized.convert("L")
    pixels = list(grayscale.getdata())

    rows = []
    for row_index in range(height):
        row_pixels = pixels[row_index * width : (row_index + 1) * width]
        # Each pixel in the row is joined into a single string
        row_chars = "".join(_map_pixel_to_char(p, ramp, invert) for p in row_pixels)
        # Each row is its own element in this list
        rows.append(row_chars)

    ascii_art = "\n".join(rows)

    return {
        "ascii_art": ascii_art,
        "width": width,
        "height": height,
        "original_width": original_width,
        "original_height": original_height,
    }

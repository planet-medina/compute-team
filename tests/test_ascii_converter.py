import io
import pytest
from PIL import Image

from ascii_converter import image_to_ascii, ASCII_RAMP


def _make_solid_image(color, size=(20, 20)):
    """Helper: build an in-memory solid-color PNG, return as bytes."""
    image = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_black_image_maps_to_darkest_char():
    image_bytes = _make_solid_image((0, 0, 0))
    result = image_to_ascii(image_bytes, width=10)
    darkest_char = ASCII_RAMP[0]
    assert all(c == darkest_char for c in result["ascii_art"] if c != "\n")


def test_white_image_maps_to_lightest_char():
    image_bytes = _make_solid_image((255, 255, 255))
    result = image_to_ascii(image_bytes, width=10)
    lightest_char = ASCII_RAMP[-1]
    assert all(c == lightest_char for c in result["ascii_art"] if c != "\n")


def test_invert_flips_mapping():
    image_bytes = _make_solid_image((0, 0, 0))
    normal = image_to_ascii(image_bytes, width=10, invert=False)
    inverted = image_to_ascii(image_bytes, width=10, invert=True)
    assert normal["ascii_art"] != inverted["ascii_art"]
    assert all(c == ASCII_RAMP[-1] for c in inverted["ascii_art"] if c != "\n")


def test_output_width_matches_request():
    image_bytes = _make_solid_image((128, 128, 128), size=(200, 100))
    result = image_to_ascii(image_bytes, width=50)
    lines = result["ascii_art"].split("\n")
    assert all(len(line) == 50 for line in lines)
    assert result["width"] == 50


def test_aspect_ratio_is_preserved_reasonably():
    # A wide image should produce a shorter ascii output (proportionally),
    # not a square one.
    wide_bytes = _make_solid_image((100, 100, 100), size=(400, 100))
    result = image_to_ascii(wide_bytes, width=100)
    # original aspect ratio 100/400 = 0.25, corrected by 0.55 char-aspect factor
    assert result["height"] < result["width"]


def test_custom_ramp_is_respected():
    image_bytes = _make_solid_image((0, 0, 0))
    result = image_to_ascii(image_bytes, width=5, ramp="AB")
    assert all(c == "A" for c in result["ascii_art"] if c != "\n")


def test_invalid_image_bytes_raises_value_error():
    with pytest.raises(ValueError):
        image_to_ascii(b"not a real image", width=10)


def test_zero_width_raises_value_error():
    image_bytes = _make_solid_image((0, 0, 0))
    with pytest.raises(ValueError):
        image_to_ascii(image_bytes, width=0)


def test_empty_ramp_raises_value_error():
    image_bytes = _make_solid_image((0, 0, 0))
    with pytest.raises(ValueError):
        image_to_ascii(image_bytes, width=10, ramp="")

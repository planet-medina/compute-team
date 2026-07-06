import io
import pytest
from PIL import Image

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def _sample_image_file(size=(20, 20), color=(10, 20, 30)):
    image = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    return buf


def test_index_page_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"ASCII Art Service" in resp.data


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_convert_success(client):
    file_data = _sample_image_file()
    resp = client.post(
        "/convert",
        data={"image": (file_data, "test.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert "ascii_art" in body
    assert body["filename"] == "test.png"
    assert body["width"] == 100  # default


def test_convert_with_custom_width(client):
    file_data = _sample_image_file()
    resp = client.post(
        "/convert?width=30",
        data={"image": (file_data, "test.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["width"] == 30


def test_convert_missing_file(client):
    resp = client.post("/convert", data={}, content_type="multipart/form-data")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_convert_invalid_width(client):
    file_data = _sample_image_file()
    resp = client.post(
        "/convert?width=abc",
        data={"image": (file_data, "test.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_convert_width_too_large(client):
    file_data = _sample_image_file()
    resp = client.post(
        "/convert?width=99999",
        data={"image": (file_data, "test.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_convert_corrupt_file(client):
    bad_file = io.BytesIO(b"this is not an image")
    resp = client.post(
        "/convert",
        data={"image": (bad_file, "bad.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_convert_download_true(client):
    file_data = _sample_image_file()
    resp = client.post(
        "/convert?download=true",
        data={"image": (file_data, "test.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    assert "text/plain" in resp.content_type
    assert resp.headers["Content-Disposition"] == 'attachment; filename="test.txt"'

    json_resp = client.post(
        "/convert",
        data={"image": (_sample_image_file(), "test.png")},
        content_type="multipart/form-data",
    )
    assert resp.data.decode("utf-8") == json_resp.get_json()["ascii_art"]


def test_convert_oversized_upload(client):
    original_limit = app.config["MAX_CONTENT_LENGTH"]
    app.config["MAX_CONTENT_LENGTH"] = 1024
    try:
        big_file = io.BytesIO(b"x" * 2048)
        resp = client.post(
            "/convert",
            data={"image": (big_file, "big.png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 413
        body = resp.get_json()
        assert "error" in body
        assert "maximum allowed size" in body["error"]
    finally:
        app.config["MAX_CONTENT_LENGTH"] = original_limit
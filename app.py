"""
app.py

HTTP service that accepts an image upload and returns a JSON response
containing an ASCII-art rendering of that image.

Run locally with:
    python app.py

Then, from another terminal, send a request using curl:
    curl -X POST "http://localhost:8080/convert?width=80&invert=false" \
      -F "image=@path/to/your/image.png"

You can optionally store your output in a file in your current directory by adding the download=true query parameter:
    curl -X POST "http://localhost:8080/convert?width=80&invert=false&download=true" \
      -F "image=@path/to/your/image.png" > output.txt
"""

from pathlib import Path

from flask import Flask, request, jsonify, make_response
from werkzeug.exceptions import RequestEntityTooLarge
from ascii_converter import image_to_ascii

app = Flask(__name__)


# Guard against too-large uploads
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

# Hard cap on requested output width, to prevent a client from requesting
# e.g. width=1000000 and blowing up memory/CPU on the server.
MAX_WIDTH = 500
DEFAULT_WIDTH = 100


def _oversized_upload_response():
    max_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
    return jsonify({"error": f"Image exceeds maximum allowed size of {max_mb}MB"}), 413


def _download_filename(original_filename: str) -> str:
    stem = Path(original_filename).stem
    return f"{stem}.txt" if stem else "ascii_art.txt"


@app.errorhandler(RequestEntityTooLarge)
def handle_oversized_upload(_error):
    return _oversized_upload_response()


@app.route("/health", methods=["GET"])
def health():
    """Basic liveness check."""
    return jsonify({"status": "ok"}), 200


@app.route("/convert", methods=["POST"])
def convert():
    """
    Accepts an image file (PNG, JPEG, etc.) and returns its ASCII art representation.

    Request:
        multipart/form-data with a field named "image" containing the file.

        Optional query string parameters:
            width    (int)  - desired output width in characters. Default 100.
            invert   (bool) - "true"/"false", default false. Character ramps
                go from dark to light by default (e.g. "@" for black pixels,
                " " for white). invert=true flips that mapping. This is useful
                if you're rendering the output on a dark terminal background
                and want the visual weight to match: dark image regions
                should look "sparse" on a dark background, not "dense".
            download (bool) - "true"/"false", default false. When true, returns
                the ASCII art as a plain-text file download instead of JSON.

    Response (200), default (download=false):
        {
            "ascii_art": "...multi-line string...",
            "width": 100,
            "height": 45,
            "original_width": 1920,
            "original_height": 1080,
            "filename": "cat.png"
        }

    Response (200), download=true:
        Plain-text body with Content-Disposition attachment (e.g. cat.txt).

    Response (400), with example error strings for each case:
        - No "image" field in the request:
            { "error": "No file provided under form field 'image'" }
        - Empty filename:
            { "error": "Empty filename" }
        - width is not an integer (e.g. width=abc):
            { "error": "width must be an integer" }
        - width outside 1-500:
            { "error": "width must be between 1 and 500" }
        - Uploaded bytes aren't a decodable image:
            { "error": "Could not read image: <underlying PIL error>" }

    Response (413):
        Upload exceeds MAX_CONTENT_LENGTH. Returned by the global
        RequestEntityTooLarge handler before this function runs.
    """
    if "image" not in request.files:
        return jsonify({"error": "No file provided under form field 'image'"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # Parse and validate the optional width parameter.
    width_param = request.args.get("width", DEFAULT_WIDTH)
    try:
        width = int(width_param)
    except ValueError:
        return jsonify({"error": "width must be an integer"}), 400

    if width <= 0 or width > MAX_WIDTH:
        return jsonify({"error": f"width must be between 1 and {MAX_WIDTH}"}), 400

    invert = request.args.get("invert", "false").lower() == "true"
    download = request.args.get("download", "false").lower() == "true"

    image_bytes = file.read()

    try:
        result = image_to_ascii(image_bytes, width=width, invert=invert)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if download:
        response = make_response(result["ascii_art"])
        response.headers["Content-Type"] = "text/plain; charset=utf-8"
        response.headers["Content-Disposition"] = (
            f'attachment; filename="{_download_filename(file.filename)}"'
        )
        return response, 200

    result["filename"] = file.filename
    return jsonify(result), 200


if __name__ == "__main__":
    # set debug=True to enable auto-reload
    app.run(host="0.0.0.0", port=8080)

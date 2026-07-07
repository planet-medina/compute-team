# ASCII Art Service

An HTTP service that accepts an image and returns an ASCII-art rendering
of it as JSON.

## 1. Building, running, and testing

### Requirements
- Python 3.9+

### Setup
In the base of the repository, run:

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run the service
In the base of the repository, run:

```bash
python app.py
```
The service listens on `http://localhost:8080`.

### Run tests
In the base of the repository, run:

```bash
python -m pytest tests/ -v
```

## 2. API specification

### `GET /health`
Liveness check.

**Example:**

Input:
```bash
curl http://localhost:8080/health
```

Output:
```json
{ "status": "ok" }
```

### `POST /convert`
Converts an uploaded image to ASCII art.

**Request:** `multipart/form-data`

| Field   | Type | Required | Description                  |
|---------|------|----------|-------------------------------|
| `image` | file | yes      | The image file to convert    |

**Query parameters:**

| Param      | Type | Default | Description                                      |
|------------|------|---------|---------------------------------------------------|
| `width`    | int  | 100     | Output width in characters (max 500)              |
| `invert`   | bool | false   | Flip dark/light mapping (useful for dark terminals)|
| `download` | bool | false   | Write the full result JSON to `ascii_art.txt` in the server's cwd |

**Example:**
```bash
curl -X POST "http://localhost:8080/convert?width=80" \
  -F "image=@cat.png"
```

**Download example:**
```bash
curl -X POST "http://localhost:8080/convert?download=true" \
  -F "image=@cat.png"
```

With `download=true`, the service writes the full success response as JSON to `ascii_art.txt` in the server's current working directory and returns the same JSON response as a normal request.

**Success response (200):**
```json
{
  "ascii_art": "@@@@%%%##**++==--::..  \n@@@%%%##**++==--::..   \n...",
  "width": 80,
  "height": 36,
  "original_width": 1920,
  "original_height": 1080,
  "filename": "cat.png"
}
```

**Error response (400):**
```json
{ "error": "width must be between 1 and 500" }
```

Common error cases: no `image` field provided, empty filename, unparsable
image bytes, `width` out of range or non-integer.

**Error response (413):**
```json
{ "error": "Image exceeds maximum allowed size of 10MB" }
```

## 3. Third-party libraries

- **Flask**: Small HTTP layer for a single JSON endpoint. Django felt like overkill for this.
- **Pillow**: Handles decoding and resizing. Most of the image work is in C, which helps.
- **pytest**: Test runner only (not a runtime dep). Fixtures are nicer than rolling everything with `unittest`.

### Conversion logic

The logic used to convert the input images to ASCII-art lives in `ascii_converter.py`. Roughly:

1. Decode the uploaded image with Pillow.
2. Resize to the requested width. Height is computed from the original aspect ratio, scaled by `0.55` to account for monospace characters being taller than they are wide (otherwise output looks stretched vertically).
3. Convert to grayscale. Color is ignored; only pixel brightness matters.
4. Map each pixel's brightness (0-255) to a character on a fixed ramp: `@%#*+=-:. ` (dark to light).
5. Join characters into rows and return the multi-line string.

With `invert=true`, brightness is flipped before mapping (handy on dark terminal backgrounds).

### Performance considerations
- Image decoding and resizing are CPU-bound and happen synchronously
  in the request thread. For the expected use case (occasional
  interactive requests) this is fine. Under sustained high load, this
  is the first place to introduce a worker pool or background queue.
  See "Known limitations" below.
- `MAX_CONTENT_LENGTH` (10 MB) and `MAX_WIDTH` (500 chars) are in place
  specifically to bound worst-case CPU/memory per request.

## Known limitations / assumptions
- Color is discarded. Output is grayscale ASCII only.
- The conversion is intentionally lossy; it does not reconstruct
  the source image pixel-by-pixel.
- Single-process, synchronous request handling with no built-in
  concurrency or queueing.

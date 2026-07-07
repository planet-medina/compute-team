# ASCII Art Service

An HTTP service that accepts an image and returns an ASCII-art rendering
of it as JSON.

---

## For Users

### Installation

**Requirements:** Python 3.9+

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Running the Service

```bash
python app.py
```
The service listens on `http://localhost:8080`.

For a production-style run:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8080 app:app
```

### API Usage Examples

#### `GET /health`
Liveness check.

```bash
curl http://localhost:8080/health
```
```json
{ "status": "ok" }
```

#### `POST /convert`
Converts an uploaded image to ASCII art.

**Request:** `multipart/form-data`

| Field   | Type | Required | Description                  |
|---------|------|----------|-------------------------------|
| `image` | file | yes      | The image file to convert    |

**Query parameters:**

| Param    | Type | Default | Description                                        |
|----------|------|---------|-----------------------------------------------------|
| `width`  | int  | 100     | Output width in characters (max 500)                |
| `invert` | bool | false   | Flip dark/light mapping (useful for dark terminals) |

**Example:**
```bash
curl -X POST "http://localhost:8080/convert?width=80" \
  -F "image=@cat.png"
```

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

**Error response (400), with example error strings for each case:**
- No `image` field provided:
  `{ "error": "No file provided under form field 'image'" }`
- Empty filename:
  `{ "error": "Empty filename" }`
- `width` is not an integer:
  `{ "error": "width must be an integer" }`
- `width` outside 1–500:
  `{ "error": "width must be between 1 and 500" }`
- Uploaded bytes aren't a decodable image:
  `{ "error": "Could not read image: <underlying PIL error>" }`

**Error response (413):** upload exceeds the 10 MB size limit.

---

## For Contributors

### Running Tests

```bash
python -m pytest tests/ -v
```

### Third-Party Libraries

- **Flask** — chosen for its minimalism and maturity (in production use
  since 2010, very stable API). This service is a single-endpoint JSON
  API with no need for the heavier feature set of something like Django;
  Flask keeps the surface area small and easy for a new teammate to
  onboard on. Well documented, huge community, good test coverage in the
  library itself.
- **Pillow** — the de facto standard image processing library for
  Python (successor to the original PIL project). Mature, actively
  maintained, wide format support (PNG/JPEG/BMP/GIF/etc. handled
  transparently), and its resize/convert operations are implemented in C
  so performance is reasonable even for moderately large images.
- **pytest** — used only for tests, not a runtime dependency. Chosen
  over the standard-library `unittest` for its more concise assertion
  syntax and fixture system (see `tests/test_app.py`'s `client` fixture).

#### Performance considerations
- Image decoding and resizing are CPU-bound and happen synchronously
  in the request thread. For the expected use case (occasional
  interactive requests) this is fine. Under sustained high load, this
  is the first place to introduce a worker pool / background queue.
- `MAX_CONTENT_LENGTH` (10 MB) and `MAX_WIDTH` (500 chars) are in place
  specifically to bound worst-case CPU/memory per request.

### Known Limitations / Assumptions
- Color is discarded — output is grayscale ASCII only. Color support
  (e.g. ANSI escape codes) is a reasonable future extension but was
  left out since raw ANSI codes are awkward to embed in a JSON string.
- The conversion is intentionally lossy; there's no way to reconstruct
  the source image from the ASCII output.
- Single-process, synchronous request handling — no built-in
  concurrency/queueing. Fine for the current scope; flagged as a
  discussion point for scaling.
-
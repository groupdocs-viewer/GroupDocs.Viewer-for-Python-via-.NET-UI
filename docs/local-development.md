# Running locally

A step-by-step for spinning up the viewer end-to-end on your machine — useful for development, demos, and capturing screenshots for the README.

## Prerequisites

- Python 3.9 – 3.14
- `git` (for cloning)
- On **Linux**: `libgdiplus`, `libfontconfig1`, `fonts-liberation`, `fonts-dejavu` system packages (the bundled `Dockerfile` lists the apt commands)
- On **macOS**: `brew install mono-libgdiplus`
- On **Windows**: nothing extra — `groupdocs-viewer-net` ships everything it needs

## 1. Clone and install

```bash
git clone https://github.com/groupdocs-viewer/GroupDocs.Viewer-for-Python-via-.NET-UI.git
cd GroupDocs.Viewer-for-Python-via-.NET-UI

python -m venv .venv
source .venv/bin/activate     # on Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

This pulls `groupdocs-viewer-net` (~193 MB wheel — first install is slow), Starlette, pydantic, uvicorn, and the dev tooling (pytest, ruff, mypy, fakeredis).

## 2. Verify the install

```bash
pytest                                    # 107 passing, ~21s
groupdocs-viewer-ui version               # → 26.4.0
```

If `pytest` complains about `groupdocs-viewer-net` symbols on Linux, double-check the system libraries from the Prerequisites section above.

## 3. Get a document to view

A starter sample DOCX lives at `tests/fixtures/sample.docx`. For screenshots / demos, anything with multiple pages and visual variety reads better — a presentation deck, an annotated PDF, a long Word doc with images.

```bash
mkdir -p documents
cp tests/fixtures/sample.docx documents/
# Add any of your own .docx / .pdf / .pptx / .xlsx files to ./documents/
```

The viewer supports 170+ formats end-to-end — drop whatever you have.

## 4. Start the server

```bash
groupdocs-viewer-ui serve --files ./documents --cache ./.viewer-cache
```

Output:

```
groupdocs-viewer-ui 26.4.0
  files:  /path/to/documents
  cache:  /path/to/.viewer-cache
  SPA:    http://127.0.0.1:8080/viewer/
  API:    http://127.0.0.1:8080/viewer-api
INFO:     Started server process [...]
INFO:     Uvicorn running on http://127.0.0.1:8080 (Press CTRL+C to quit)
```

## 5. Open the SPA

Navigate to **http://127.0.0.1:8080/viewer/** in your browser.

You should see:

- A header with the GroupDocs logo and language selector
- A toolbar with zoom, page navigation, search, print, download, present buttons
- A thumbnail pane on the left
- Your documents listed when you click **Open File** in the toolbar
- The selected document rendered in the main pane

## 6. Capture a good screenshot

For the README cover image (`docs/images/viewer-ui.png`):

1. Open a document with multiple pages and visual variety (a pitch deck or annotated PDF works well).
2. Wait for the first page to render fully (you should see clean text + any images / charts).
3. Confirm thumbnails have populated on the left pane.
4. Use a viewport ratio that matches typical README rendering — **~1400×900 px** is a good target. On macOS, `Cmd + Shift + 4` then drag captures a region; on Windows, Snipping Tool works.
5. Save to `docs/images/viewer-ui.png`. Optimize with `pngquant` or similar if it lands above 500 KB.

For a controls-callout image (matching the .NET project's `viewer-ui-controls.png`), capture at the same dimensions and add labels in your image editor pointing at: header, toolbar, thumbnails pane, page controls, zoom selector, search, print, download, present, language switcher.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `groupdocs-viewer-ui: command not found` | Forgot `source .venv/bin/activate` (or installed without `pip install -e .`) |
| `FileNotFoundException` on document load | The `--files` directory isn't writable or the file path has Unicode that the .NET runtime mangles |
| Pages render but text is missing on Linux | Missing fonts — install `fonts-liberation` and `fonts-dejavu` |
| `ImportError: ... [s3]` / `[azure]` / `[redis]` | Optional extra not installed — `pip install ".[s3]"` etc. |
| SPA shows "Loading..." forever | Browser blocked the API call — check the browser network tab; usually a CORS or path mismatch |
| Cache lookups never hit | `--cache` not passed, or the directory isn't persistent across restarts |

## Mounting in your own app instead

The CLI is for quick demos. For real apps, see [`examples/02_fastapi_basic/`](../examples/02_fastapi_basic/) (FastAPI), [`examples/03_flask_basic/`](../examples/03_flask_basic/) (Flask), or any of the other examples — each is a self-contained `python main.py` you can copy into your project.

# UI for GroupDocs.Viewer for Python via .NET

[![PyPI](https://img.shields.io/pypi/v/groupdocs-viewer-net-ui?label=groupdocs-viewer-net-ui)](https://pypi.org/project/groupdocs-viewer-net-ui/)
[![Python](https://img.shields.io/pypi/pyversions/groupdocs-viewer-net-ui)](https://pypi.org/project/groupdocs-viewer-net-ui/)

<!-- Hero image hosted on the groupdocs-viewer.github.io repo so PyPI renders
     it. PyPI ignores relative paths in the README. The same file lives at
     docs/images/viewer-ui.jpg for repo-local viewing. -->
![GroupDocs.Viewer UI](https://raw.githubusercontent.com/groupdocs-viewer/groupdocs-viewer.github.io/master/resources/image/python-ui/viewer-ui.jpg)

A web UI for [`groupdocs-viewer-net`](https://pypi.org/project/groupdocs-viewer-net/) — view 190+ document and image formats in a browser. Mount inside an existing FastAPI / Flask / Django app, or run standalone via the bundled CLI.

The frontend is the same battle-tested Angular SPA from the [GroupDocs.Viewer for .NET UI](https://github.com/groupdocs-viewer/GroupDocs.Viewer-for-.NET-UI) project, vendored into this package — one `pip install` and you're done.

## Install

```bash
pip install groupdocs-viewer-net-ui
```

Optional cloud-storage / cache backends:

```bash
pip install "groupdocs-viewer-net-ui[s3]"      # S3FileStorage
pip install "groupdocs-viewer-net-ui[azure]"   # AzureBlobFileStorage
pip install "groupdocs-viewer-net-ui[redis]"   # RedisCache
pip install "groupdocs-viewer-net-ui[all]"
```

## Run it

### CLI (zero config)

```bash
groupdocs-viewer-ui serve --files ./documents --cache ./.viewer-cache
# → http://127.0.0.1:8080/viewer/
```

### Docker

```bash
docker compose up
# Drop documents into ./documents on the host
```

### In code

```python
from groupdocs_viewer_ui import Config, create_app
from groupdocs_viewer_ui.cache.local import LocalFileCache
from groupdocs_viewer_ui.storage.local import LocalFileStorage
from groupdocs_viewer_ui.viewer.selfhost import SelfHostViewer

storage = LocalFileStorage("./Files")
app = create_app(
    Config(),
    storage=storage,
    cache=LocalFileCache("./Cache"),
    viewer=SelfHostViewer(storage=storage),
)
# Run with: uvicorn myapp:app
```

`create_app()` returns a Starlette ASGI app — mount it under FastAPI directly, or bridge to Flask/Django with [`a2wsgi`](https://github.com/abersheeran/a2wsgi). See [`examples/`](./examples/) for runnable patterns.

## Configure

`Config()` accepts knobs for rendering mode, preload count, initial zoom, UI toggles (header, toolbar, thumbnails, search, print, etc.), localization, branding, and routing. See [`AGENTS.md`](./AGENTS.md#configuration) for the full field reference.

```python
Config(
    rendering_mode="html",        # or "image"
    preload_pages=3,
    initial_zoom="Fit Page",      # or "Fit Width", "Fit Height", "100%", "75%", etc.
    enable_thumbnails=True,
    ui_title="My Document Viewer",
    custom_css="<style>:root { --c-bg-brand: #0d9488; }</style>",
)
```

## Storage backends

Built-in: `LocalFileStorage`, `S3FileStorage` (`[s3]` extra), `AzureBlobFileStorage` (`[azure]` extra). Implement the [`FileStorage`](./src/groupdocs_viewer_ui/storage/protocol.py) protocol for anything else — three async methods. See [`examples/05_custom_storage/`](./examples/05_custom_storage/) for a SQLite-backed example.

## Cache backends

Built-in: `InMemoryCache`, `LocalFileCache`, `RedisCache` (`[redis]` extra). When you supply both `viewer` and `cache` to `create_app()`, the viewer is auto-wrapped in a `CachingViewer` decorator — no manual composition required. Implement the [`FileCache`](./src/groupdocs_viewer_ui/cache/protocol.py) protocol for custom backends. See [`examples/06_custom_cache/`](./examples/06_custom_cache/) for a TTL wrapper.

## Authentication

```python
from starlette.exceptions import HTTPException

async def require_session(request):
    if request.cookies.get("session") not in VALID_SESSIONS:
        raise HTTPException(status_code=401, detail="Login required")

app = create_app(..., auth_check=require_session)
```

The check runs before every `/viewer-api/*` request. `/health`, the SPA, and static assets are deliberately not guarded — wrap the whole app yourself if you need broader scope. See [`examples/07_auth/`](./examples/07_auth/) for session-cookie + bearer-token patterns.

For rate limiting, pair with [`slowapi`](https://github.com/laurentS/slowapi) or [`asgi-ratelimit`](https://github.com/abersheeran/asgi-ratelimit) as standard Starlette middleware.

## Examples

| Path | Shows |
|---|---|
| [`examples/01_cli_quickstart/`](./examples/01_cli_quickstart/) | Zero-config CLI demo |
| [`examples/02_fastapi_basic/`](./examples/02_fastapi_basic/) | Mount in FastAPI |
| [`examples/03_flask_basic/`](./examples/03_flask_basic/) | Mount in Flask via `a2wsgi` |
| [`examples/04_custom_branding/`](./examples/04_custom_branding/) | Custom logo + CSS |
| [`examples/05_custom_storage/`](./examples/05_custom_storage/) | SQLite `FileStorage` |
| [`examples/06_custom_cache/`](./examples/06_custom_cache/) | TTL `FileCache` decorator |
| [`examples/07_auth/`](./examples/07_auth/) | Session cookie + bearer token auth |

## Linux

`groupdocs-viewer-net` needs `libgdiplus`, `libfontconfig1`, `fonts-liberation`, and `fonts-dejavu` for rendering. The bundled `Dockerfile` installs them; for bare metal:

```bash
sudo apt-get install -y libgdiplus libfontconfig1 fontconfig fonts-liberation fonts-dejavu
```

On Linux/macOS `groupdocs-viewer-net` runs on `GroupDocs.Viewer.CrossPlatform`, which renders every format **except** Project (MPP, MPT, MPX) and PSD — those are Windows-only. Everything else, including Visio, works on all platforms.

## Documentation

- [`AGENTS.md`](./AGENTS.md) — full reference: config fields, protocols, extensibility, gotchas
- [`examples/`](./examples/) — runnable end-to-end demos for each integration pattern
- [GroupDocs.Viewer for Python via .NET docs](https://docs.groupdocs.com/viewer/python-net/)

## Development

```bash
pip install -e ".[dev]"
pytest                         # 107 passing (~21s; 5 e2e tests render a real DOCX)
ruff check src tests
mypy src
```

## License

MIT — see [`LICENSE`](./LICENSE).

## Support

- [Free support forum](https://forum.groupdocs.com/)
- [Paid support helpdesk](https://helpdesk.groupdocs.com/)

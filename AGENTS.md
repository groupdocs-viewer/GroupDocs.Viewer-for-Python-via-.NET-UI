# AGENTS.md — `groupdocs-viewer-net-ui` reference

This file is the deep reference an AI coding assistant should consult before generating, modifying, or debugging code that uses `groupdocs-viewer-net-ui`. Everything here is concrete: API surface, configuration fields, extensibility seams, common pitfalls, and the architectural decisions that aren't obvious from skimming the source.

The user-facing [`README.md`](./README.md) covers the marketing summary. **Use this file for anything beyond "what is this package".**

---

## Table of contents

1. [Architecture](#architecture)
2. [The canonical wiring pattern](#the-canonical-wiring-pattern)
3. [Configuration](#configuration)
4. [Storage backends](#storage-backends)
5. [Cache backends](#cache-backends)
6. [Viewer engine](#viewer-engine)
7. [Authentication](#authentication)
8. [HTTP API contracts](#http-api-contracts)
9. [CLI reference](#cli-reference)
10. [Docker](#docker)
11. [Custom branding](#custom-branding)
12. [Pitfalls and gotchas](#pitfalls-and-gotchas)
13. [Testing](#testing)

---

## Architecture

The package is a Starlette ASGI app composed of:

- **A vendored Angular SPA** at `src/groupdocs_viewer_ui/frontend/` — same compiled bundle the .NET project ships. Served as static files; `index.html` is rendered through a small template that injects a JSON config block read by `window.groupdocs.viewer`.
- **9 HTTP endpoints** under `Config.api_path` (default `/viewer-api`) that match the .NET `ViewerController` wire format byte-for-byte. The vendored SPA talks to these unchanged.
- **Three Protocol-shaped extension seams**: `FileStorage` (where documents live), `FileCache` (where rendered output is persisted), and `Viewer` (the rendering engine itself).
- **A `CachingViewer` decorator** that wraps any `Viewer` with cache-aside reads/writes against a `FileCache`. Auto-applied by `create_app()` when both `viewer` and `cache` are supplied.

Everything is async-signatured. The default `SelfHostViewer` wraps the synchronous `groupdocs-viewer-net` library by offloading every call through `asyncio.to_thread`.

The runtime never imports cloud SDKs (`aioboto3`, `azure-storage-blob`) at module-level — they're behind extras and imported lazily inside the corresponding storage class. The same applies to `redis`. This keeps `pip install groupdocs-viewer-net-ui` slim.

## The canonical wiring pattern

```python
from groupdocs_viewer_ui import Config, create_app
from groupdocs_viewer_ui.cache.local import LocalFileCache
from groupdocs_viewer_ui.storage.local import LocalFileStorage
from groupdocs_viewer_ui.viewer.selfhost import SelfHostViewer

storage = LocalFileStorage("./Files")            # ← shared instance

app = create_app(
    Config(),
    storage=storage,                              # ← storage goes to create_app
    cache=LocalFileCache("./Cache"),
    viewer=SelfHostViewer(storage=storage),       # ← AND to SelfHostViewer
)
```

**The same `storage` instance must be passed to both `create_app(storage=...)` and `SelfHostViewer(storage=...)`.** This is not a code smell — see [Pitfalls](#pitfalls-and-gotchas) for why.

`create_app()` returns a `starlette.applications.Starlette` instance. Run it with any ASGI server:

```bash
uvicorn myapp:app --host 0.0.0.0 --port 8080
```

### Mounting under FastAPI

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"viewer": "/viewer/"}

# Mount LAST. Mount("/", ...) catches every path underneath, so anything
# added after the mount can never be reached.
app.mount("/", create_app(Config(), storage=storage, cache=cache, viewer=viewer))
```

### Mounting under Flask / Django (WSGI)

Bridge ASGI → WSGI with `a2wsgi`, then dispatch by path:

```python
from a2wsgi import ASGIMiddleware

viewer_wsgi = ASGIMiddleware(create_app(Config(), storage=storage, ...))

_VIEWER_PATHS = ("/viewer", "/viewer-api", "/health")

def application(environ, start_response):
    if environ["PATH_INFO"].startswith(_VIEWER_PATHS):
        return viewer_wsgi(environ, start_response)
    return flask_app.wsgi_app(environ, start_response)
```

**Do not use `werkzeug.middleware.dispatcher.DispatcherMiddleware`** — it strips the matched prefix from `PATH_INFO`, and the viewer's routes need the full path. See `examples/03_flask_basic/`.

## Configuration

`Config` is a frozen-style dataclass — construct it once, pass to `create_app()`. Every field is optional with a sensible default.

### Routing

| Field | Default | Notes |
|---|---|---|
| `ui_path` | `"/viewer"` | URL prefix for the SPA |
| `ui_title` | `"GroupDocs.Viewer"` | Browser tab title |
| `api_path` | `"viewer-api"` | URL prefix for the API |
| `use_absolute_urls` | `False` | When True, page/thumb URLs include the full origin |
| `api_domain` | `""` | Required when `use_absolute_urls=True` |

### Rendering

| Field | Default | Notes |
|---|---|---|
| `rendering_mode` | `"html"` | Or `"image"`. Match this on `SelfHostViewer(rendering_mode=...)` too. The literal string is the EXACT value the .NET `RenderingMode.Value` emits (lowercase) — the SPA matches it as-is. |
| `static_content_mode` | `False` | Reserved — backend doesn't yet pre-generate static content. |
| `preload_pages` | `3` | First N pages render on document open. `0` = render all. |
| `initial_file` | `None` | Path inside storage to open on startup. Also overridable via `?file=`. |
| `initial_zoom` | `"Fit Page"` | One of `"Fit Page"`, `"Fit Width"`, `"Fit Height"`, or a percent string `"25%"`, `"50%"`, `"60%"`, `"70%"`, `"75%"`, `"80%"`, `"90%"`, `"100%"`, `"125%"`, `"150%"`, `"200%"`, `"300%"`. The fit / percent strings are the EXACT values the .NET `ZoomLevel.Value` emits — the space and the `%` matter. **`"Fit Page"` is supported by the vendored SPA but is not in the .NET `ZoomLevel` enum** — use `"Fit Width"` or `"Fit Height"` instead if you need wire compatibility with the .NET API. |

### UI toggles (all default `True`)

![SPA controls labeled](https://raw.githubusercontent.com/groupdocs-viewer/groupdocs-viewer.github.io/master/resources/image/python-ui/viewer-ui-tour.jpg)

The image above labels each piece of SPA chrome the toggles below control. Local mirror: `docs/images/viewer-ui-tour.jpg`.

| Field | Hides |
|---|---|
| `enable_header` | The header bar |
| `enable_toolbar` | The toolbar |
| `enable_file_browser` | Open File button |
| `enable_file_upload` | Upload inside the file browser |
| `enable_thumbnails` | Thumbnail pane |
| `enable_search` | Search button (HTML mode only) |
| `enable_page_selector` | Page-number input |
| `enable_zoom` | Zoom selector |
| `enable_file_name` | File name in header |
| `enable_print` | Print button |
| `enable_download_pdf` | Download PDF button |
| `enable_presentation` | Present button |
| `enable_context_menu` | Right-click context menu |
| `enable_hyperlinks` | Clickable links in HTML pages |
| `enable_help` | Help button + hotkey popup |
| `enable_language_selector` | Language switcher |

### Localization

| Field | Default | Notes |
|---|---|---|
| `default_language` | `"en"` | Language code (`en`, `de`, `fr`, ...) |
| `supported_languages` | `["en"]` | List of codes shown in the language switcher |

Default language can be overridden via `?lang=de` query string.

### Branding

| Field | Default | Notes |
|---|---|---|
| `custom_css` | `""` | HTML block spliced into `<head>`. Wrap in `<style>` tags yourself. |
| `custom_js` | `""` | HTML block spliced before the closing `<gd-viewer>` tag. |
| `hide_logo_image` | `False` | Replaces logo with empty SVG |
| `custom_logo_image_path` | `None` | Path to SVG; serves at `/viewer/assets/ui/logo-image.svg` |
| `hide_logo_text` | `False` | Same as above for the wordmark |
| `custom_logo_text_path` | `None` | Path to SVG; serves at `/viewer/assets/ui/logo-text.svg` |

### HTTP caching

| Field | Default | Notes |
|---|---|---|
| `response_cache_duration_seconds` | `0` | Browser cache for rendered page/thumb responses. `0` → `Cache-Control: no-cache, no-store`. |

## Storage backends

Storage backends implement the [`FileStorage`](./src/groupdocs_viewer_ui/storage/protocol.py) protocol — three async methods plus a `FileSystemEntry` dataclass:

```python
@dataclass
class FileSystemEntry:
    file_path: str
    is_directory: bool
    size: int = 0

class FileStorage(Protocol):
    async def list_dirs_and_files(self, dir_path: str) -> list[FileSystemEntry]: ...
    async def read_file(self, file_path: str) -> bytes: ...
    async def write_file(self, file_name: str, data: bytes, *, rewrite: bool = False) -> str: ...
```

### `LocalFileStorage`

```python
from groupdocs_viewer_ui.storage.local import LocalFileStorage
storage = LocalFileStorage("./Files")
```

Path-traversal protected (attempts to escape the root raise `PermissionError`). Hidden files (dot-prefixed) are skipped from listings.

### `S3FileStorage` (`[s3]` extra)

```python
from groupdocs_viewer_ui.storage.s3 import S3FileStorage
storage = S3FileStorage("my-bucket", prefix="documents/")
```

Uses the standard AWS credential chain (env vars, shared config, IAM role). Pass `client_factory=` to inject custom credentials, an alternate endpoint (LocalStack), or a fake for tests.

### `AzureBlobFileStorage` (`[azure]` extra)

```python
from groupdocs_viewer_ui.storage.azure import AzureBlobFileStorage
storage = AzureBlobFileStorage(
    "documents",
    connection_string="DefaultEndpointsProtocol=https;AccountName=...",
    prefix="archive/",
)
```

Pass `container_factory=` for SAS-token wiring or test fakes.

### Custom storage

```python
class HttpFileStorage:
    """Read-only storage that fetches files over HTTP."""
    def __init__(self, manifest_url): ...

    async def list_dirs_and_files(self, dir_path):
        # fetch a manifest, return entries
        ...

    async def read_file(self, file_path):
        async with httpx.AsyncClient() as c:
            return (await c.get(file_path)).content

    async def write_file(self, file_name, data, *, rewrite=False):
        raise NotImplementedError("HttpFileStorage is read-only")
```

Pass to both `create_app(storage=...)` AND `SelfHostViewer(storage=...)`.

## Cache backends

Cache backends implement the [`FileCache`](./src/groupdocs_viewer_ui/cache/protocol.py) protocol — bytes-in / bytes-out:

```python
class FileCache(Protocol):
    async def try_get(self, cache_key: str, file_path: str) -> bytes | None: ...
    async def set(self, cache_key: str, file_path: str, data: bytes) -> None: ...
    async def remove(self, file_path: str) -> None: ...
```

Cache keys follow .NET conventions (see [`cache/keys.py`](./src/groupdocs_viewer_ui/cache/keys.py)):

- `info.json` — `DocumentInfo` for a file
- `file.pdf` — generated PDF
- `p{N}{ext}` — page N (e.g. `p1.html`, `p3.png`)
- `p{N}_t{ext}` — thumb for page N
- `p{N}_{resource}` — HTML-mode external resource

`CachingViewer` handles JSON serialization for `DocumentInfo`. Pages, thumbs, PDFs, and resources are stored as raw bytes.

### `InMemoryCache`, `LocalFileCache`, `RedisCache`

```python
from groupdocs_viewer_ui.cache.memory import InMemoryCache    # process-local
from groupdocs_viewer_ui.cache.local import LocalFileCache    # disk
from groupdocs_viewer_ui.cache.redis import RedisCache        # multi-instance ([redis] extra)

cache = RedisCache(url="redis://localhost:6379/0")
```

`RedisCache.remove` uses `SCAN` (not `KEYS`) so it's safe on large keyspaces.

### Custom cache

Decorator pattern — wrap any existing cache:

```python
class TTLCache:
    def __init__(self, inner: FileCache, *, ttl_seconds: float = 3600): ...
    async def try_get(self, cache_key, file_path):
        # check timestamp, fall through to inner if fresh
        ...
```

See `examples/06_custom_cache/`.

### Auto-wrapping

`create_app()` automatically wraps the supplied `viewer` in `CachingViewer(viewer, cache)` when `cache` is non-None. Don't compose the decorator manually unless you have a specific reason — `app.state.viewer` will be the wrapped instance.

## Viewer engine

The default `SelfHostViewer` wraps `groupdocs-viewer-net`. It's the only viewer implementation shipped in the package. Other implementations would satisfy the [`Viewer`](./src/groupdocs_viewer_ui/viewer/protocol.py) Protocol.

```python
SelfHostViewer(
    rendering_mode="html",                  # or "image"
    storage=storage,                        # REQUIRED, see Pitfalls
    thumb_width=300,                        # px width for thumbnails
    html_external_resources=False,          # see below
    resource_url_template_factory=None,     # required if html_external_resources=True
)
```

### HTML embedded vs external resources

By default HTML pages are self-contained — CSS, fonts, and images are inlined into each page's HTML. To switch to external resources (better caching when many pages share the same assets):

```python
from groupdocs_viewer_ui.api.url_builder import ApiUrlBuilder

url_builder = ApiUrlBuilder(api_path="viewer-api")
viewer = SelfHostViewer(
    rendering_mode="html",
    storage=storage,
    html_external_resources=True,
    resource_url_template_factory=url_builder.build_resource_url_template,
)
```

The `resource_url_template_factory` callable returns a URL template with literal `{0}` and `{1}` placeholders that `groupdocs.viewer` substitutes at render time (page number, resource name). The factory MUST emit URLs that include `api_path` because the browser fetches resources straight from inline HTML — no SPA URL prepending in front.

In external mode, `get_page` returns a `Page` with a populated `resources` list. The wrapping `CachingViewer` caches each resource so subsequent `/get-resource` requests hit cache. If a resource request arrives cold (cache empty), `SelfHostViewer.get_page_resource` re-renders the page on demand to satisfy it.

## Authentication

```python
from starlette.exceptions import HTTPException
from starlette.requests import Request

async def my_check(request: Request) -> None:
    if not authorized(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

app = create_app(..., auth_check=my_check)
```

### Scope

The `auth_check` runs ONLY for requests under `Config.api_path` (default `/viewer-api/*`). Deliberately not guarded:

- `/health` (liveness probe)
- `/viewer/` (SPA index)
- `/viewer/<asset>` (static assets)
- Any other route the user mounts

To guard the broader scope, wrap the whole returned Starlette app in your own middleware.

### Pattern: session cookie (works with the SPA out of the box)

```python
async def require_session(request: Request) -> None:
    if request.cookies.get("session") not in VALID_SESSIONS:
        raise HTTPException(status_code=401, detail="Login required")
```

Cookies are sent automatically with same-origin `fetch()` calls, so the SPA works once the user has logged in.

### Pattern: bearer token (server-to-server)

```python
async def require_bearer(request: Request) -> None:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    if auth[7:] not in VALID_TOKENS:
        raise HTTPException(status_code=403, detail="Invalid token")
```

The SPA does NOT inject `Authorization` headers natively — bearer tokens work for `curl` / API clients but not for browser-driven viewer flows. Use cookies for SPA, tokens for API-only callers, or both at once (`examples/07_auth/`).

### Error response shape

When auth_check raises `HTTPException`, the middleware emits:

```json
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{"error": "Login required"}
```

### Rate limiting

Not built-in. Pair with [`slowapi`](https://github.com/laurentS/slowapi) or [`asgi-ratelimit`](https://github.com/abersheeran/asgi-ratelimit) and wrap the returned Starlette app or its `/viewer-api/*` mount.

## HTTP API contracts

All shapes match the .NET `GroupDocs.Viewer.UI.Api.Models` namespace byte-for-byte (camelCase JSON). Pydantic models in [`api/contracts.py`](./src/groupdocs_viewer_ui/api/contracts.py) enforce wire format.

### Endpoints

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/list-dir` | `{path: str}` | `[{path, name, isDir, size}]` |
| POST | `/upload-file` | `multipart` (file or `url=`, optional `rewrite=`) | `{file: str}` |
| POST | `/view-data` | `{file, fileType?, password?}` | `{file, fileType, fileName, canPrint, searchTerm, pages: [...]}` |
| POST | `/create-pages` | `{file, fileType?, password?, pages: [int]}` | `[{number, width, height, pageUrl, thumbUrl?}]` |
| POST | `/create-pdf` | `{file, fileType?, password?}` | `{pdfUrl: str}` |
| GET | `/get-page?file=&page=` | — | binary (HTML or image bytes) |
| GET | `/get-thumb?file=&page=` | — | binary (PNG) |
| GET | `/get-pdf?file=` | — | binary (PDF, with `Content-Disposition: attachment`) |
| GET | `/get-resource?file=&page=&resource=` | — | binary (CSS/font/image) — only in `html_external_resources` mode |

### `PageData`

```json
{
  "number": 1,
  "width": 612,
  "height": 792,
  "pageUrl": "/get-page?file=sample.docx&page=1",
  "thumbUrl": "/get-thumb?file=sample.docx&page=1"
}
```

`pageUrl` is `null` for pages that haven't been rendered yet. `thumbUrl` is `null` outside HTML mode (image mode has no separate thumb stream).

### Password handling

Document password errors return:

```json
HTTP/1.1 403 Forbidden
{"error": "Password Required"}    // when no password was sent
{"error": "Incorrect Password"}   // when a wrong password was sent
```

## CLI reference

```
groupdocs-viewer-ui serve [OPTIONS]
```

| Option | Default | |
|---|---|---|
| `-f, --files PATH` | `cwd` | Document directory |
| `-c, --cache PATH` | _(disabled)_ | On-disk cache directory |
| `-H, --host TEXT` | `127.0.0.1` | |
| `-p, --port INTEGER` | `8080` | |
| `-m, --rendering-mode TEXT` | `html` | `html` or `image` |
| `--ui-path TEXT` | `/viewer` | |
| `--api-path TEXT` | `viewer-api` | |
| `--html-external-resources` | _off_ | External CSS/font/image resources |

`groupdocs-viewer-ui version` prints the package version.

## Docker

The repo includes `Dockerfile` + `docker-compose.yml` at the root. The image runs:

```
ENTRYPOINT groupdocs-viewer-ui serve --host 0.0.0.0 --port 8080 \
                                      --files /docs --cache /cache
```

Volumes: `/docs` (mount document directory), `/cache` (mount persistent cache).

To pass extra CLI flags, override the command:

```yaml
services:
  viewer:
    build: .
    command: ["groupdocs-viewer-ui", "serve",
              "--host", "0.0.0.0", "--port", "8080",
              "--files", "/docs", "--cache", "/cache",
              "--rendering-mode", "image"]
```

First build is slow (~5–10 min) because `groupdocs-viewer-net` is a ~193 MB wheel. Subsequent builds reuse the cached layer.

## Custom branding

The `custom_logo_*_path` fields read the SVG file once at app construction and serve the bytes at `/viewer/assets/ui/logo-image.svg` and `/viewer/assets/ui/logo-text.svg`. These routes are registered BEFORE the `StaticFiles` mount, so they shadow the vendored bytes.

`hide_logo_image=True` and `hide_logo_text=True` serve an empty SVG placeholder (`<svg xmlns="http://www.w3.org/2000/svg"/>`) — same behavior as the .NET `ReplaceLogoResources`.

`custom_css` and `custom_js` are spliced into the SPA `index.html` template at request time. Wrap your CSS in `<style>` tags and your JS in `<script>` tags — the values are inserted as-is.

## Pitfalls and gotchas

### `SelfHostViewer` requires a `storage` instance

The `creds.file_path` value sent in API requests is a relative path inside the storage root (e.g. `"sample.docx"`). Passing it straight to `groupdocs.viewer.Viewer(path)` resolves it against the **process cwd**, not the storage root, and fails with `FileNotFoundException`. Cloud-storage paths wouldn't work at all.

The viewer routes file input through `storage.read_file(creds.file_path)` first, then hands a `BytesIO` stream to `groupdocs.viewer`. This is why `SelfHostViewer` takes a required `storage` keyword arg.

**Always share the same `storage` instance** between `create_app(storage=...)` and `SelfHostViewer(storage=...)`. Don't construct two separate instances pointing at the same root — it works but signals the wrong intent.

### FastAPI mount order matters

`app.mount("/", viewer_app)` catches every path underneath. Routes added AFTER the mount are unreachable. Always:

```python
@app.get("/")           # ← register your routes FIRST
def root(): ...

@app.get("/api/...")
def api(): ...

app.mount("/", viewer_app)   # ← mount LAST
```

### Don't use Werkzeug's `DispatcherMiddleware` for Flask integration

`DispatcherMiddleware` strips the matched prefix from `PATH_INFO` before forwarding. The viewer's routes need the full path (`/viewer/main.js`, not `/main.js`), so dispatched requests silently 404 every static asset. Use a hand-rolled dispatcher that forwards without rewriting paths — see `examples/03_flask_basic/`.

### Auth middleware catches `HTTPException` itself

The auth middleware (`_AuthCheckMiddleware` in `app.py`) catches `HTTPException` and converts it to a JSON response in the middleware itself. Starlette's built-in `ExceptionMiddleware` sits BELOW this layer in the stack, so a raised exception here would result in `RuntimeError: Caught handled exception, but response already started.`

If you ever refactor this and think "the framework can handle this exception" — re-run `tests/test_auth_hook.py` first. The obvious-looking simplification reintroduces the bug.

### Multi-prefix mount is not supported (yet)

`Config(ui_path="/")` doesn't currently work — the wiring in `create_app()` assumes `ui_path` is non-empty and non-root. If you need to mount the viewer at a sub-path like `/myapp/viewer`, the cleanest workaround is to set `ui_path="/myapp/viewer"` directly (matching the actual mount point) and configure your outer app to route those paths to the viewer.

### `groupdocs-viewer-net` Linux dependencies

On Linux, `groupdocs-viewer-net` needs system libraries for image rendering. The bundled `Dockerfile` installs them; bare-metal Linux users need:

```bash
sudo apt-get install -y libgdiplus libfontconfig1 fontconfig fonts-liberation fonts-dejavu
```

Without these, rendering succeeds for some formats but fails (sometimes silently) for others — usually anything that needs font metrics.

### `static_content_mode` is reserved

`Config.static_content_mode` exists for parity with the .NET wire format but the backend doesn't yet pre-generate static content. Setting it to `True` will confuse the SPA. Leave it `False`.

### Search is wire-only

`Config.enable_search=True` shows the search UI in the SPA, but there's no server-side search implementation — the SPA does client-side search across loaded pages. For full-document search you'd need to add `ISearchTermResolver`-equivalent extensibility (not yet shipped).

## Testing

```bash
pip install -e ".[dev]"
pytest                         # 107 passing, ~21s
```

Test layout:

| File | What it covers |
|---|---|
| `test_config.py` | Config defaults |
| `test_contracts.py` | Pydantic JSON shape (camelCase) |
| `test_url_builder.py` | URL construction with/without absolute URLs, resource templates |
| `test_local_storage.py` | LocalFileStorage CRUD + path traversal protection |
| `test_s3_storage.py` | S3FileStorage via hand-rolled S3 fake (no moto required) |
| `test_azure_storage.py` | AzureBlobFileStorage via hand-rolled container fake |
| `test_cache_memory.py` | InMemoryCache |
| `test_cache_local.py` | LocalFileCache, including disk-survival across instances |
| `test_redis_cache.py` | RedisCache via `fakeredis` |
| `test_caching_viewer.py` | CachingViewer cache-aside, batched gets, auto-wrap |
| `test_routes.py` | All 9 endpoints with FakeViewer |
| `test_app_wiring.py` | SPA serving, static assets, logo override, /health |
| `test_auth_hook.py` | auth_check scope (only `/viewer-api/*`) and behaviour |
| `test_cli.py` | CLI version + arg validation (does NOT actually start uvicorn) |
| `test_selfhost_external.py` | Structural tests for HTML-external mode (no real render) |
| `test_e2e.py` | **Real `groupdocs.viewer` rendering** through the full HTTP stack — auto-skips when the lib isn't installed |

When changing anything that touches the rendering path, run the E2E suite. It's the only thing that exercises real document parsing — everything else uses `FakeViewer`.

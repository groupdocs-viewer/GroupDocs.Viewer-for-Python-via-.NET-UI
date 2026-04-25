# Changelog

All notable changes to `groupdocs-viewer-net-ui` are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project follows the GroupDocs `YY.MM.0` versioning scheme.

## [Unreleased]

## [26.4.0] — 2026-04-25

Initial public release. Feature-complete port of the [GroupDocs.Viewer for .NET UI](https://github.com/groupdocs-viewer/GroupDocs.Viewer-for-.NET-UI) to Python.

### Added

- **`create_app()` ASGI factory** — returns a Starlette app exposing the viewer UI + API. Mountable inside FastAPI/Starlette, bridgeable to Flask/Django via `a2wsgi`.
- **Vendored Angular SPA** at `src/groupdocs_viewer_ui/frontend/` — same compiled bundle as the .NET project (commit `b9a222f`, .NET tag `26.3.0-5-gb9a222f`).
- **9 viewer API endpoints** — `list-dir`, `upload-file`, `view-data`, `create-pages`, `create-pdf`, `get-page`, `get-thumb`, `get-pdf`, `get-resource`. Wire format matches the .NET `ViewerController` byte-for-byte (camelCase JSON via pydantic).
- **Pluggable storage backends** via the `FileStorage` Protocol:
  - `LocalFileStorage` (built-in)
  - `S3FileStorage` (`[s3]` extra; lazy `aioboto3`)
  - `AzureBlobFileStorage` (`[azure]` extra; lazy `azure-storage-blob`)
- **Pluggable cache backends** via the `FileCache` Protocol:
  - `InMemoryCache`, `LocalFileCache` (built-in)
  - `RedisCache` (`[redis]` extra; lazy `redis.asyncio`)
- **`CachingViewer` decorator** — auto-applied by `create_app()` when both `viewer` and `cache` are supplied. Batched `get_pages` / `get_thumbs` only re-render misses.
- **`SelfHostViewer`** — wraps `groupdocs-viewer-net`. Renders to a tempdir per call, reads bytes back, offloads sync work via `asyncio.to_thread`. Reads source bytes via the `FileStorage` Protocol so cloud storage works transparently.
- **HTML-with-external-resources rendering** — opt in via `html_external_resources=True` + `resource_url_template_factory`. Resources are rendered alongside pages and cached.
- **Custom branding** — `Config.custom_css`, `Config.custom_js`, `Config.custom_logo_image_path`, `Config.custom_logo_text_path`, plus `hide_logo_image` / `hide_logo_text` for hiding without replacing.
- **Auth hook** — `create_app(auth_check=...)` accepts an async callable applied as middleware to `/viewer-api/*` only. `/health` and the SPA itself are deliberately not guarded.
- **CLI** — `groupdocs-viewer-ui serve` boots a development server with sensible defaults. `--html-external-resources` and `--rendering-mode` flags.
- **Docker** — `Dockerfile` (Python 3.12 slim + `libgdiplus`/`libfontconfig1`/font packages) and `docker-compose.yml` for one-command deployment.
- **107 tests** — including 5 E2E tests in `tests/test_e2e.py` that exercise real `groupdocs-viewer-net` rendering through the full HTTP stack (`view-data`, HTML/PNG page rendering, PDF generation, thumb generation). Auto-skip when the lib isn't installed.
- **7 examples** in `examples/` — CLI quickstart, FastAPI mount, Flask integration, custom branding, custom storage (SQLite), custom cache (TTL wrapper), and authentication (session cookie + bearer token hybrid).

### Notes

- Python 3.9-3.14 supported.
- Optional cloud-SDK extras (`aioboto3`, `azure-storage-blob`, `redis`) are imported lazily — installing the package without extras keeps the dependency surface minimal.
- The vendored SPA's HTTP contracts mirror the .NET project, so updates flow downstream — pull a new SPA build with `python scripts/sync_frontend.py`.

[Unreleased]: https://github.com/groupdocs-viewer/GroupDocs.Viewer-for-Python-via-.NET-UI/compare/v26.4.0...HEAD
[26.4.0]: https://github.com/groupdocs-viewer/GroupDocs.Viewer-for-Python-via-.NET-UI/releases/tag/v26.4.0

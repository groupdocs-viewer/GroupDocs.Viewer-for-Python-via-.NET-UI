# CLI Quickstart

Zero-config: drop documents in a folder, point the CLI at it, open the browser.

```bash
pip install groupdocs-viewer-net-ui
mkdir docs
cp ~/Documents/*.docx ~/Documents/*.pdf docs/

groupdocs-viewer-ui serve --files ./docs --cache ./.viewer-cache
# → SPA at http://127.0.0.1:8080/viewer/
```

## What the CLI does

`serve` wires up:

- `LocalFileStorage` rooted at `--files`
- `LocalFileCache` at `--cache` (omit the flag to disable caching)
- `SelfHostViewer` wrapping `groupdocs-viewer-net`
- A `uvicorn` process serving the resulting ASGI app

## Useful flags

| Flag | Default | What it does |
|---|---|---|
| `--files DIR` | cwd | Document root |
| `--cache DIR` | _(disabled)_ | Where to persist rendered pages between runs |
| `--port N` | 8080 | HTTP port |
| `--host H` | 127.0.0.1 | Bind address |
| `--rendering-mode html\|image` | html | HTML preserves text/search; image is a screenshot |

## When to graduate

When you need authentication, custom storage, or to embed the viewer in
an existing web app, switch from the CLI to `create_app(...)` directly —
see `examples/02_fastapi_basic/`.

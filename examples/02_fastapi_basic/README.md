# FastAPI Basic

Mount the viewer into an existing FastAPI app at the root, alongside your own routes.

```bash
pip install groupdocs-viewer-net-ui fastapi uvicorn
python main.py
# → SPA at  http://127.0.0.1:8000/viewer/
# → your routes still at  /, /api/health
```

## How it works

`create_app(...)` returns a Starlette ASGI app. Starlette is what FastAPI is built on, so `app.mount("/", viewer_app)` works directly — no adapter required.

The viewer's internal paths under the mount:

| URL | What it is |
|---|---|
| `/viewer/` | SPA index |
| `/viewer/main.js`, `/viewer/styles.css`, ... | Vendored Angular assets |
| `/viewer-api/list-dir`, `/viewer-api/view-data`, ... | The 9 viewer endpoints |
| `/health` | The viewer's liveness probe |

## Key constraint: route order

`Mount("/", ...)` matches every request that doesn't match an earlier explicit route. So **register your own FastAPI routes before mounting the viewer** — anything added after the mount will never be reached.

## Adding auth

Wrap the mounted app in middleware before the routes match. M5 will ship a first-class auth hook; until then, any Starlette `Middleware` works.

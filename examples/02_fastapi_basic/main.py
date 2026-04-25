"""Minimal FastAPI app with the viewer mounted at the root.

Run: ``python main.py`` then open http://127.0.0.1:8000/viewer/
"""
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from groupdocs_viewer_ui import Config, create_app
from groupdocs_viewer_ui.cache.local import LocalFileCache
from groupdocs_viewer_ui.storage.local import LocalFileStorage
from groupdocs_viewer_ui.viewer.selfhost import SelfHostViewer

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"
CACHE = ROOT / ".viewer-cache"
DOCS.mkdir(exist_ok=True)

app = FastAPI(title="My App with Document Viewer")


# Register YOUR routes BEFORE mounting the viewer.
# Mount("/") catches every path underneath, so anything added after the
# mount can never be reached.
@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Document viewer is at /viewer/"}


@app.get("/api/health")
def app_health() -> dict[str, str]:
    return {"status": "ok"}


# Mount last. The viewer serves /viewer/* (SPA), /viewer-api/* (API), and
# /health (its own probe) — all under this mount.
storage = LocalFileStorage(DOCS)
viewer_app = create_app(
    Config(),
    storage=storage,
    cache=LocalFileCache(CACHE),
    viewer=SelfHostViewer(storage=storage),
)
app.mount("/", viewer_app)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

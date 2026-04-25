"""Flask app with the viewer mounted alongside via a manual WSGI dispatch.

Run: ``python main.py`` then open http://127.0.0.1:5000/viewer/
"""
from pathlib import Path

from a2wsgi import ASGIMiddleware
from flask import Flask

from groupdocs_viewer_ui import Config, create_app
from groupdocs_viewer_ui.cache.local import LocalFileCache
from groupdocs_viewer_ui.storage.local import LocalFileStorage
from groupdocs_viewer_ui.viewer.selfhost import SelfHostViewer

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"
CACHE = ROOT / ".viewer-cache"
DOCS.mkdir(exist_ok=True)


flask_app = Flask(__name__)


@flask_app.route("/")
def hello() -> str:
    return (
        "<h1>Flask + Viewer</h1>"
        "<p>The viewer lives at <a href='/viewer/'>/viewer/</a>.</p>"
    )


@flask_app.route("/api/health")
def app_health() -> dict[str, str]:
    return {"status": "ok"}


storage = LocalFileStorage(DOCS)
viewer_asgi = create_app(
    Config(),
    storage=storage,
    cache=LocalFileCache(CACHE),
    viewer=SelfHostViewer(storage=storage),
)
viewer_wsgi = ASGIMiddleware(viewer_asgi)

# Werkzeug's DispatcherMiddleware would also work but it STRIPS the matched
# prefix from PATH_INFO before forwarding — and viewer_asgi's routes expect
# the full path (e.g. ``/viewer/main.js``, not ``/main.js``). The simplest
# correct integration is a hand-rolled dispatcher that forwards without
# rewriting paths:
_VIEWER_PATHS = ("/viewer", "/viewer-api", "/health")


def application(environ, start_response):
    if environ["PATH_INFO"].startswith(_VIEWER_PATHS):
        return viewer_wsgi(environ, start_response)
    return flask_app.wsgi_app(environ, start_response)


if __name__ == "__main__":
    from wsgiref.simple_server import make_server

    print("Serving at http://127.0.0.1:5000")
    print("  Flask:  /, /api/health")
    print("  Viewer: /viewer/, /viewer-api/*, /health")
    make_server("127.0.0.1", 5000, application).serve_forever()

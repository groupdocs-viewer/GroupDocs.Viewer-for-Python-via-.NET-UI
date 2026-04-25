"""Viewer protected by a session-cookie check.

The SPA loads the cookie automatically with same-origin fetches, so the
viewer works end-to-end once the user has logged in. For API-only callers
(curl, server-to-server), a header check works the same way — see
``allow_session_or_token`` for a hybrid example.
"""
from pathlib import Path

import uvicorn
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route

from groupdocs_viewer_ui import Config, create_app
from groupdocs_viewer_ui.cache.local import LocalFileCache
from groupdocs_viewer_ui.storage.local import LocalFileStorage
from groupdocs_viewer_ui.viewer.selfhost import SelfHostViewer

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)

# In real life: look up sessions in Redis/DB. Hard-coded here for demo.
VALID_SESSIONS = {"alice-session", "bob-session"}
VALID_TOKENS = {"server-token-123"}


async def allow_session_or_token(request: Request) -> None:
    """Allow if EITHER a known session cookie OR a known bearer token is present."""
    session = request.cookies.get("session")
    if session in VALID_SESSIONS:
        return
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:]
        if token in VALID_TOKENS:
            return
    raise HTTPException(status_code=401, detail="Authentication required")


# Tiny "login" endpoint outside the viewer mount — sets the session cookie
# so a browser session can reach /viewer-api/* afterwards. In a real app
# this would be your existing auth flow; the viewer doesn't care how the
# cookie got there.
async def login(_request: Request) -> Response:
    response = PlainTextResponse("Logged in. Open /viewer/ in your browser.")
    response.set_cookie(
        "session", "alice-session", httponly=True, samesite="lax", path="/"
    )
    return response


storage = LocalFileStorage(DOCS)
app = create_app(
    Config(),
    storage=storage,
    cache=LocalFileCache(ROOT / ".viewer-cache"),
    viewer=SelfHostViewer(storage=storage),
    auth_check=allow_session_or_token,
)
# Add the /login route after create_app so it's not behind the auth check.
app.routes.insert(0, Route("/login", login, methods=["GET"]))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)

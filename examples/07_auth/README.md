# Auth-Protected Viewer

Gate `/viewer-api/*` behind a session cookie or a bearer token.

## How

```python
async def my_check(request):
    if not authorized(request):
        raise HTTPException(status_code=401, detail="Authentication required")

app = create_app(..., auth_check=my_check)
```

`auth_check` is invoked for every request hitting `/viewer-api/*`. The check returns `None` to allow, raises `HTTPException` to deny. The middleware catches the exception and returns a JSON `{"error": detail}` body with the chosen status code.

## What is and isn't guarded

| Path | Guarded? |
|---|---|
| `/viewer-api/*` (the 9 viewer endpoints) | **yes** |
| `/viewer/`, `/viewer/main.js`, `/viewer/styles.css`, ... (SPA + assets) | no |
| `/health` (liveness probe) | no |
| Any other route you mount | no |

The middleware is applied to the API mount only. To guard the SPA chrome itself, wrap the whole returned Starlette app in your own middleware.

## Try it

```bash
pip install groupdocs-viewer-net-ui uvicorn
python main.py
# In another terminal:
curl -i http://127.0.0.1:8080/viewer-api/list-dir -d '{"path":""}' -H "Content-Type: application/json"
# → 401 {"error":"Authentication required"}

# With a session cookie (visit /login first to get one):
curl http://127.0.0.1:8080/login -c cookies.txt
curl -b cookies.txt http://127.0.0.1:8080/viewer-api/list-dir -d '{"path":""}' -H "Content-Type: application/json"
# → 200 [...]

# With a bearer token (server-to-server):
curl -H "Authorization: Bearer server-token-123" \
     http://127.0.0.1:8080/viewer-api/list-dir -d '{"path":""}' -H "Content-Type: application/json"
# → 200 [...]
```

## Why session cookies for the SPA

The SPA uses plain `fetch()` for API calls. Cookies sent on the page request are sent on the fetch too (same-origin). Bearer tokens would require modifying the SPA to inject an `Authorization` header — not impossible (intercept fetch globally) but more work than worth it.

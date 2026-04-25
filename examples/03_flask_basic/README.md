# Flask Basic

Add the viewer to an existing Flask app via WSGI dispatch.

```bash
pip install groupdocs-viewer-net-ui flask a2wsgi
python main.py
# → SPA at  http://127.0.0.1:5000/viewer/
# → Flask routes still at  /, /api/health
```

## How it works

Flask is WSGI, the viewer is ASGI. `a2wsgi.ASGIMiddleware` wraps the viewer
so it speaks WSGI, then a tiny dispatcher routes paths beginning with
`/viewer`, `/viewer-api`, or `/health` to the viewer and everything else
to Flask.

We use a hand-rolled dispatcher rather than `werkzeug.middleware.dispatcher.DispatcherMiddleware`
because the latter strips the matched prefix from `PATH_INFO`, but the
viewer's routes expect the full path (e.g. `/viewer/main.js`, not `/main.js`).

## Django

Same pattern — Django is WSGI, so wrap the viewer with `ASGIMiddleware`,
mount the dispatcher in front of `django.core.wsgi.get_wsgi_application()`,
and configure `urls.py` to handle everything else.

# Custom Branding

Replace the GroupDocs logo with your own and inject custom CSS to restyle the SPA's chrome.

## What this example does

- Sets `ui_title="MyApp Document Viewer"` (browser tab + SPA header)
- Hides the small square logo via `hide_logo_image=True`
- Replaces the wordmark (`logo-text.svg`) with `branding/custom-logo.svg`
- Splices `branding/custom.css` into the SPA's `<head>` via `custom_css`

The same `Config` knobs let you replace either logo, hide either logo, change the page title, or inject `<script>` tags via `custom_js`.

## Run

```bash
pip install groupdocs-viewer-net-ui uvicorn
python main.py
# → http://127.0.0.1:8080/viewer/
```

## Under the hood

`create_app` registers a route at `/viewer/assets/ui/logo-text.svg` that serves the bytes you supplied **before** the StaticFiles mount, so it shadows the vendored asset. Logo bytes are read from disk once at app construction and held in memory.

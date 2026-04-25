"""Custom branding — replace the GroupDocs logo and inject custom CSS."""
from pathlib import Path

import uvicorn

from groupdocs_viewer_ui import Config, create_app
from groupdocs_viewer_ui.cache.local import LocalFileCache
from groupdocs_viewer_ui.storage.local import LocalFileStorage
from groupdocs_viewer_ui.viewer.selfhost import SelfHostViewer

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)

custom_css = (ROOT / "branding" / "custom.css").read_text(encoding="utf-8")

storage = LocalFileStorage(DOCS)
app = create_app(
    Config(
        ui_title="MyApp Document Viewer",
        # Hide the square logo and replace the wordmark with our own SVG.
        hide_logo_image=True,
        custom_logo_text_path=str(ROOT / "branding" / "custom-logo.svg"),
        # Splice an inline <style> block into the SPA's <head>.
        custom_css=f"<style>{custom_css}</style>",
    ),
    storage=storage,
    cache=LocalFileCache(ROOT / ".viewer-cache"),
    viewer=SelfHostViewer(storage=storage),
)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)

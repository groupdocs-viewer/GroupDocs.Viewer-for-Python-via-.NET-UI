"""Structural tests for SelfHostViewer's HTML-external-resources mode.

We don't exercise the actual rendering path here (that needs the real
``groupdocs.viewer`` library + a sample document — covered by manual /
integration runs). These tests pin down the constructor contract and
the behaviour of ``get_page_resource`` in non-external mode.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from groupdocs_viewer_ui.api.url_builder import ApiUrlBuilder
from groupdocs_viewer_ui.storage.local import LocalFileStorage
from groupdocs_viewer_ui.viewer.entities import FileCredentials
from groupdocs_viewer_ui.viewer.selfhost import SelfHostViewer


@pytest.fixture
def storage(tmp_path: Path) -> LocalFileStorage:
    return LocalFileStorage(tmp_path)


def test_external_mode_requires_url_template_factory(storage):
    with pytest.raises(ValueError, match="resource_url_template_factory"):
        SelfHostViewer(
            rendering_mode="html", storage=storage, html_external_resources=True
        )


def test_external_mode_rejects_image_rendering(storage):
    with pytest.raises(ValueError, match="rendering_mode='html'"):
        SelfHostViewer(
            rendering_mode="image",
            storage=storage,
            html_external_resources=True,
            resource_url_template_factory=lambda f: "/r?f={0}&p={1}",
        )


def test_external_mode_accepts_url_builder_factory(storage):
    builder = ApiUrlBuilder(api_path="viewer-api")
    viewer = SelfHostViewer(
        rendering_mode="html",
        storage=storage,
        html_external_resources=True,
        resource_url_template_factory=builder.build_resource_url_template,
    )
    assert viewer.page_extension == ".html"


def test_default_construction_keeps_embedded_html(storage):
    viewer = SelfHostViewer(storage=storage)
    assert viewer._html_external_resources is False
    assert viewer._resource_url_template_factory is None


@pytest.mark.asyncio
async def test_get_page_resource_raises_in_embedded_mode(storage):
    viewer = SelfHostViewer(storage=storage)
    with pytest.raises(NotImplementedError, match="external-resources"):
        await viewer.get_page_resource(
            FileCredentials(file_path="/a.docx"), 1, "styles.css"
        )

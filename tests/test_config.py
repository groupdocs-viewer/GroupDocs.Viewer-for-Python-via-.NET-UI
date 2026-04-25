from groupdocs_viewer_ui import Config


def test_defaults():
    c = Config()
    # rendering_mode and initial_zoom carry the EXACT strings the .NET
    # RenderingMode.Value / ZoomLevel.Value properties emit — the vendored
    # Angular SPA matches these as literals.
    assert c.rendering_mode == "html"
    assert c.initial_zoom == "Fit Page"
    assert c.preload_pages == 3
    assert c.enable_toolbar is True
    assert c.enable_file_browser is True
    assert c.default_language == "en"
    assert c.supported_languages == ["en"]


def test_routing_defaults():
    c = Config()
    assert c.ui_path == "/viewer"
    assert c.api_path == "viewer-api"
    assert c.use_absolute_urls is False
    assert c.api_domain == ""


def test_supported_languages_is_independent_per_instance():
    a = Config()
    b = Config()
    a.supported_languages.append("fr")
    assert b.supported_languages == ["en"]
